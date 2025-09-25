#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para limpeza de arquivos de log antigos.
Procura recursivamente por arquivos .logs com mais de 3 dias
e os remove do sistema.

Uso:
    python clean_old_logs.py [diretório]
    
    Se nenhum diretório for especificado, usa o diretório atual.
"""

import os
import sys
import time
from datetime import datetime, timedelta
import logging

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_old_file(file_path, days=3):
    """
    Verifica se um arquivo é mais antigo que o número de dias especificado.
    
    Args:
        file_path (str): Caminho do arquivo
        days (int): Número de dias para considerar um arquivo como antigo
        
    Returns:
        bool: True se o arquivo for mais antigo que o número de dias especificado
    """
    try:
        # Obtém o timestamp da última modificação do arquivo
        file_time = os.path.getmtime(file_path)
        # Converte para datetime
        file_datetime = datetime.fromtimestamp(file_time)
        # Calcula a data limite
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return file_datetime < cutoff_date
    except Exception as e:
        logger.error(f"Erro ao verificar data do arquivo {file_path}: {str(e)}")
        return False

def clean_old_logs(directory):
    """
    Procura recursivamente por arquivos .logs antigos e os remove.
    
    Args:
        directory (str): Diretório base para iniciar a busca
    """
    try:
        total_removed = 0
        total_size_freed = 0
        
        logger.info(f"Iniciando limpeza de logs em: {directory}")
        
        # Percorre o diretório recursivamente
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.logs'):
                    file_path = os.path.join(root, file)
                    
                    if is_old_file(file_path):
                        try:
                            # Obtém o tamanho do arquivo antes de remover
                            file_size = os.path.getsize(file_path)
                            
                            # Remove o arquivo
                            os.remove(file_path)
                            
                            total_removed += 1
                            total_size_freed += file_size
                            
                            logger.info(f"Arquivo removido: {file_path}")
                        except Exception as e:
                            logger.error(f"Erro ao remover arquivo {file_path}: {str(e)}")
        
        # Converte o tamanho para MB para exibição
        size_in_mb = total_size_freed / (1024 * 1024)
        
        logger.info(f"Limpeza concluída!")
        logger.info(f"Total de arquivos removidos: {total_removed}")
        logger.info(f"Espaço liberado: {size_in_mb:.2f} MB")
        
    except Exception as e:
        logger.error(f"Erro durante a limpeza: {str(e)}")

def main():
    """Função principal do script"""
    try:
        # Usa o diretório passado como argumento ou o diretório atual
        directory = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
        
        if not os.path.isdir(directory):
            logger.error(f"Diretório não encontrado: {directory}")
            sys.exit(1)
            
        clean_old_logs(directory)
        
    except KeyboardInterrupt:
        logger.info("\nOperação cancelada pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 