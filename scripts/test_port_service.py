import uvicorn
from fastapi import FastAPI
from datetime import datetime
import serial.tools.list_ports

app = FastAPI()

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/ports')
def get_ports():
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            'port': p.device,
            'description': p.description
        })
    print(f'Returning {len(ports)} ports')
    return {'ports': ports, 'count': len(ports)}

if __name__ == '__main__':
    print('Starting test service on port 8004...')
    uvicorn.run(app, host='0.0.0.0', port=8004, log_level='info')
