import sys
import logging

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_ports():
    try:
        logger.info('Attempting to import serial.tools.list_ports...')
        import serial.tools.list_ports
        logger.info(f'serial module: {serial.tools.list_ports.__file__}')
        
        logger.info('Calling comports()...')
        raw_ports = serial.tools.list_ports.comports()
        logger.info(f'comports() returned: {type(raw_ports)}')
        
        ports = list(raw_ports)
        logger.info(f'Found {len(ports)} ports')
        
        result = []
        for p in ports:
            logger.debug(f'Port: {p.device} - {p.description}')
            result.append({'port': p.device, 'description': p.description})
        
        return result
    except Exception as e:
        logger.error(f'Error in _get_ports: {e}', exc_info=True)
        return []

if __name__ == '__main__':
    ports = _get_ports()
    print(f'Result: {len(ports)} ports')
