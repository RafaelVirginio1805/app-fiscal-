from flask import Flask, render_template, request
import os
import pandas as pd
import mysql.connector
from datetime import datetime
import utm

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Caminho do CSV
CSV_PATH = 'data/cidades.csv'
os.makedirs('data', exist_ok=True)

CSV_PATH1 = 'data/tipo.csv'
os.makedirs('data', exist_ok=True)

# Criar CSV se não existir
if not os.path.exists(CSV_PATH):
    dados_iniciais = {
        'cidade': ['Salvador', 'Salvador', 'Feira de Santana'],
        'bairro': ['Brotas', 'Pituba', 'Centro']
    }
    pd.DataFrame(dados_iniciais).to_csv(CSV_PATH, index=False)

# Carregar CSV para dicionário
def carregar_cidades():
    df = pd.read_csv(CSV_PATH)
    cidades_dict = {}
    for _, row in df.iterrows():
        cidade = row['CIDADE'].strip().title()
        bairro = row['BAIRRO'].strip().title()
        cidades_dict.setdefault(cidade, []).append(bairro)
    return cidades_dict

def carregar_tipo():
    df = pd.read_csv(CSV_PATH1)
    return df['TIPO'].dropna().str.strip().str.title().unique().tolist()

@app.route('/')
def index():
    cidades_dict = carregar_cidades()
    tipos = carregar_tipo()
    return render_template('form.html', cidades=cidades_dict, tipos=tipos)

@app.route('/enviar', methods=['POST'])
def enviar():
    cidade = request.form['cidade']
    logradouro = request.form['logradouro']
    numero = request.form['numero']
    bairro = request.form['bairro']
    barramento = request.form.get('barramento', '')

    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    lat = lon = utm_x = utm_y = utm_zone_number = utm_zone_letter = None

    if latitude and longitude:
        try:
            lat = float(latitude)
            lon = float(longitude)
            utm_result = utm.from_latlon(lat, lon)
            utm_x, utm_y, utm_zone_number, utm_zone_letter = utm_result
        except Exception as e:
            print("Erro ao converter coordenadas UTM:", e)

    # Fotos do poste (múltiplas)
    fotos_poste = request.files.getlist('foto_poste[]')
    caminhos_fotos_poste = [salvar_foto(f, prefix='poste') for f in fotos_poste if f]
    fotos_poste_str = ';'.join(caminhos_fotos_poste)

    index = 0
    while True:
        key = f'ocupante_nome_{index}'
        if key not in request.form:
            break

        ocupante = request.form.get(f'ocupante_nome_{index}')
        if not ocupante:
            index += 1
            continue  # pula se foi removido ou está vazio

        nivel = request.form.get(f'nivel_fixacao_{index}')
        tipo_cabo = request.form.get(f'tipo_cabo_{index}')
        equipamento = request.form.get(f'equipamento_{index}')
        placa = request.form.get(f'placa_identificacao_{index}')
        irregularidades = request.form.get(f'irregularidades_{index}')

        fotos_ocupante = request.files.getlist(f'foto_ocupante_{index}[]')
        caminhos_fotos_ocupante = [salvar_foto(f, prefix=f'ocupante_{index}') for f in fotos_ocupante if f]
        fotos_ocupante_str = ';'.join(caminhos_fotos_ocupante)

        salvar_no_banco(
            cidade, logradouro, numero, bairro, barramento, ocupante,
            nivel, tipo_cabo, equipamento, placa,
            irregularidades, fotos_ocupante_str, fotos_poste_str,
            lat, lon, utm_x, utm_y, utm_zone_number, utm_zone_letter
        )

        index += 1

    return f"<h2>{index} ocupante(s) registrado(s)!</h2><a href='/'>Voltar</a>"

def salvar_foto(file, prefix):
    if file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{prefix}_{timestamp}.jpg"
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        return path
    return ''

def salvar_no_banco(cidade, logradouro, numero, bairro, barramento, ocupante,
                    nivel, tipo_cabo, equipamento, placa,
                    irregularidades, fotos_ocupante, fotos_poste,
                    latitude, longitude, utm_x, utm_y, utm_zone_number, utm_zone_letter):
    try:
        latitude = float(latitude) if latitude is not None else None
        longitude = float(longitude) if longitude is not None else None
        utm_x = float(utm_x) if utm_x is not None else None
        utm_y = float(utm_y) if utm_y is not None else None
        utm_zone_number = int(utm_zone_number) if utm_zone_number is not None else None
        utm_zone_letter = str(utm_zone_letter) if utm_zone_letter is not None else None

        conexao = mysql.connector.connect(
            host='localhost',
            user='root',
            password='1234',
            database='app_fiscal'
        )
        cursor = conexao.cursor()
        query = """
            INSERT INTO registros (
                cidade, logradouro, numero, bairro, barramento, ocupante,
                nivel_fixacao, tipo_cabo, equipamento, placa_identificacao,
                irregularidades, foto_ocupante_path, foto_poste_path,
                latitude, longitude, utm_x, utm_y, utm_zone_number, utm_zone_letter, data_hora
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        valores = (
            cidade, logradouro, numero, bairro, barramento, ocupante,
            nivel, tipo_cabo, equipamento, placa,
            irregularidades, fotos_ocupante, fotos_poste,
            latitude, longitude, utm_x, utm_y, utm_zone_number, utm_zone_letter
        )
        cursor.execute(query, valores)
        conexao.commit()
        cursor.close()
        conexao.close()
    except mysql.connector.Error as err:
        print(f"Erro ao inserir no banco: {err}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
