#!/usr/bin/env python3
'''
PersonaPlex WebRTC Server - January 29, 2026

Low-latency WebRTC transport for PersonaPlex full-duplex voice.
Target: sub-200ms latency for natural conversation.

Uses aiortc for WebRTC implementation.
'''

import asyncio
import json
import logging
import os
from uuid import uuid4

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRecorder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HOST = os.getenv('WEBRTC_HOST', '0.0.0.0')
PORT = int(os.getenv('WEBRTC_PORT', '8997'))
PERSONAPLEX_WS = os.getenv('PERSONAPLEX_WS_URL', 'ws://localhost:8998')

pcs = set()  # Active peer connections


async def offer(request):
    '''Handle WebRTC offer from client'''
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
    
    pc = RTCPeerConnection()
    pc_id = str(uuid4())[:8]
    pcs.add(pc)
    
    logger.info(f'WebRTC peer connected: {pc_id}')
    
    @pc.on('connectionstatechange')
    async def on_connectionstatechange():
        logger.info(f'Connection state: {pc.connectionState}')
        if pc.connectionState == 'failed':
            await pc.close()
            pcs.discard(pc)
    
    @pc.on('track')
    def on_track(track):
        logger.info(f'Track received: {track.kind}')
        if track.kind == 'audio':
            # Forward audio to PersonaPlex for processing
            asyncio.create_task(process_audio_track(pc, track))
    
    # Set remote description and create answer
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return web.json_response({
        'sdp': pc.localDescription.sdp,
        'type': pc.localDescription.type,
        'peer_id': pc_id,
    })


async def process_audio_track(pc, track):
    '''Process incoming audio track'''
    logger.info('Processing audio track...')
    # This would connect to PersonaPlex WebSocket and stream audio
    # For now, just log frames
    try:
        while True:
            frame = await track.recv()
            # TODO: Send to PersonaPlex for processing
    except Exception as e:
        logger.info(f'Audio track ended: {e}')


async def health(request):
    '''Health check endpoint'''
    return web.json_response({
        'status': 'healthy',
        'service': 'personaplex-webrtc',
        'active_peers': len(pcs),
        'port': PORT,
    })


async def on_shutdown(app):
    '''Cleanup on shutdown'''
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def create_app():
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get('/health', health)
    app.router.add_post('/offer', offer)
    return app


if __name__ == '__main__':
    logger.info(f'PersonaPlex WebRTC Server starting on http://{HOST}:{PORT}')
    web.run_app(create_app(), host=HOST, port=PORT)
