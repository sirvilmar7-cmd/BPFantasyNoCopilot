import zipfile
import os

def criar_backup():
    arquivos_para_salvar = [
        'app.py', 
        'index.html', 
        'importar_csv.py', 
        'elencos_brutos.csv', 
        'elencos.json'
    ]
    nome_zip = 'Backup_Projeto_Atual.zip'
    
    with zipfile.ZipFile(nome_zip, 'w') as zipf:
        for arquivo in arquivos_para_salvar:
            if os.path.exists(arquivo):
                zipf.write(arquivo)
                print(f"Adicionado: {arquivo}")
            else:
                print(f"Atenção: {arquivo} não encontrado, ignorado.")
    
    print(f"\nBackup concluído com sucesso: {nome_zip}")

if __name__ == '__main__':
    criar_backup()