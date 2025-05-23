from flask import Flask, render_template, request
import os
import mysql.connector
from datetime import datetime
import utm

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('form.html')

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

    total = int(request.form.get('total_ocupantes', 0))
    for i in range(total):
        ocupante = request.form.get(f'ocupante_nome_{i}')
        nivel = request.form.get(f'nivel_fixacao_{i}')
        tipo_cabo = request.form.get(f'tipo_cabo_{i}')
        equipamento = request.form.get(f'equipamento_{i}')
        placa = request.form.get(f'placa_identificacao_{i}')
        irregularidades = request.form.get(f'irregularidades_{i}')

        fotos_ocupante = request.files.getlist(f'foto_ocupante_{i}[]')
        caminhos_fotos_ocupante = [salvar_foto(f, prefix=f'ocupante_{i}') for f in fotos_ocupante if f]
        fotos_ocupante_str = ';'.join(caminhos_fotos_ocupante)

        salvar_no_banco(
            cidade, logradouro, numero, bairro, barramento, ocupante,
            nivel, tipo_cabo, equipamento, placa,
            irregularidades, fotos_ocupante_str, fotos_poste_str,
            lat, lon, utm_x, utm_y, utm_zone_number, utm_zone_letter
        )

    return f"<h2>{total} ocupante(s) registrado(s)!</h2><a href='/'>Voltar</a>"

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
