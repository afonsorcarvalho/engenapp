from odoo import http
from odoo.http import request, content_disposition
import os
import base64
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import logging


_logger = logging.getLogger(__name__)

class FileDownloadController(http.Controller):

    @http.route('/web/content/download_file_txt_to_pdf_qweb/<int:record_id>', type='http', auth="user")
    def download_file_txt_to_pdf_qweb(self, record_id, **kwargs):
        """
        Rota para gerar PDF do arquivo TXT usando QWeb com cabeçalho padrão Odoo
        
        Args:
            record_id (int): ID do registro do ciclo
            
        Returns:
            Response: PDF gerado com cabeçalho Odoo
        """
        record = request.env['afr.supervisorio.ciclos'].browse(record_id)
        
        # Verifica se arquivo existe
        if not record.file_path or not os.path.exists(record.file_path):
            return request.not_found()
            
        try:
            # Lê conteúdo do TXT
            with open(record.file_path, 'r', encoding='utf-8') as file:
                txt_content = file.read().replace('\x00', '')
            _logger.info(f"txt_content: {txt_content}")
            # Prepara dados para o template
            data = {
              
                'doc_ids': [record.id],
                'doc_model': 'afr.supervisorio.ciclos',
                'docs': record,
            }
            
            # Gera PDF usando QWeb
            pdf = request.env.ref('afr_supervisorio_ciclos.action_report_txt_to_pdf')._render_qweb_pdf([record.id], data=data)[0]
            
            # Nome do arquivo
            filename = os.path.basename(record.file_path).replace('.txt', '.pdf')
            
            # Retorna PDF
            return request.make_response(
                pdf,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', content_disposition(filename))
                ]
            )
            
        except Exception as e:
            return request.not_found(f"Erro ao gerar PDF: {str(e)}")

    @http.route('/web/content/download_file_txt_to_pdf/<int:record_id>', type='http', auth="user")
    def download_file_txt_to_pdf(self, record_id, **kwargs):
        record = request.env['afr.supervisorio.ciclos'].browse(record_id)
        
        msg_rodape = f"Ciclo cod.: {record.name} - Gerado pelo sistema FITADIGITAL"
        pagina = 1
        rodape_x = 130
        rodape_y = 10
        text_size = 8
        leading = 0.1
        line_space = 8
        # Verifica se o arquivo existe
        if not record.file_path or not os.path.exists(record.file_path):
            return request.not_found()
        
        try:
            # Lê o arquivo TXT
            with open(record.file_path, 'r', encoding='utf-8') as file:
                txt_content = file.read().replace('\x00', '')
           
            # Cria um buffer para o PDF
            pdf_buffer = BytesIO()
            
            # Cria o PDF
            pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
            
            # Define a fonte como Courier para manter o formato monospace
            pdf.setFont('Courier', text_size, leading=leading)
            
            pdf.drawString(rodape_x,rodape_y,msg_rodape + " - Página " + str(pagina))
           
            y = 800  # Posição inicial do texto
            
            # Divide o conteúdo em linhas
            lines = txt_content.split('\n')
            
            # Adiciona cada linha ao PDF
            for line in lines:
                if y < 50:  # Se chegou ao fim da página
                    pdf.showPage()  # Nova página
                    pdf.setFont('Courier', text_size, leading=leading)  # Precisa redefinir a fonte para nova página
                    pagina += 1
                    pdf.drawString(rodape_x,rodape_y,msg_rodape + " - Página " + str(pagina))
                    y = 800  # Reset posição Y
                
                pdf.drawString(50, y, line)
                y -= line_space  # Espaço entre linhas
            
            lines = record.cycle_statistics_txt.split('\n')
            y = 800 
            
            pdf.showPage()  # Nova página
            pagina += 1
            pdf.setFont('Courier', text_size, leading=leading)  # Precisa redefinir a fonte para nova página
            pdf.drawString(rodape_x,rodape_y,msg_rodape + " - Página " + str(pagina))
            for line in lines:
                if y < 50:  # Se chegou ao fim da página
                    pdf.showPage()  # Nova página
                    pdf.setFont('Courier', text_size, leading=leading)  # Precisa redefinir a fonte para nova página
                    pagina += 1
                    pdf.drawString(rodape_x,rodape_y,msg_rodape + " - Página " + str(pagina))
                    y = 800  # Reset posição Y

                pdf.drawString(50, y, line)
                y -= line_space  # Espaço entre linhas
            
            pdf.save()
            
            # Prepara o conteúdo do PDF
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            # Nome do arquivo para download
            filename = os.path.basename(record.file_path).replace('.txt', '.pdf')
            
            # Retorna o PDF
            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', content_disposition(filename))
                ]
            )
            
        except Exception as e:
            return request.not_found(str(e))  

    @http.route('/web/content/download_file_txt/<int:record_id>', type='http', auth="user")
    def download_file(self, record_id, **kwargs):
        record = request.env['afr.supervisorio.ciclos'].browse(record_id)
        
        # Verifique se o arquivo existe
        if not record.file_path or not os.path.exists(record.file_path):
            return request.not_found()
        
        # Lê o arquivo
        try:
            with open(record.file_path, 'rb') as file:
                file_content = file.read()
        except Exception as e:
            return request.not_found(str(e))
        
        # Nome do arquivo para download
        filename = os.path.basename(record.file_path)
        
        # Retorna o conteúdo com os headers apropriados
        return request.make_response(
            file_content,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )
