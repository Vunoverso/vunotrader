"""
Módulo de logging e alertas.
"""

import logging

# ...existing code...

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# TODO: Adicionar handlers de arquivo e envio de alertas
def log_info(message: str):
    logger.info(message)

def log_error(message: str):
    logger.error(message)
