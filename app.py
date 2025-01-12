from flask import Flask, request, jsonify, render_template
import requests
import psycopg2
from config import DB_CONFIG, GOOGLE_BOOKS_API_URL
import os
from urllib.parse import urlparse
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# Pega a URL do banco de dados da variável de ambiente (Heroku)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgres://uf3uml6ni9h6js:pdef26903eaaf81e4645b81426de68949f195b3114e97581349dacdcde3254cf6@c9pv5s2sq0i76o.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dbgdoj5djua7n7')

# Função para conectar ao banco de dados
def conectar_banco():
    try:
        # Divide a URL do banco de dados em partes
        result = urlparse(DATABASE_URL)
        conexao = psycopg2.connect(
            database=result.path[1:],  # Remove o prefixo '/' do dbname
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        print("Conexão bem-sucedida!")  # Apenas para confirmar a conexão
        return conexao
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None


# Rota para a página inicial (index)
@app.route('/')
def index():
    return render_template('index.html')

# Pesquisar livros na API do Google Books
@app.route('/pesquisar', methods=['GET'])
def pesquisar_livros():
    consulta = request.args.get('consulta')
    if not consulta:
        return jsonify({"erro": "Parâmetro de consulta ausente"}), 400
    
    resposta = requests.get(GOOGLE_BOOKS_API_URL, params={'q': consulta})
    if resposta.status_code != 200:
        return jsonify({"erro": "Falha ao buscar dados na API do Google Books"}), 500
    
    livros = resposta.json().get('items', [])
    resultados = []
    for livro in livros:
        info_volume = livro.get('volumeInfo', {})
        resultados.append({
            "id_google": livro.get('id'),
            "titulo": info_volume.get('title', 'Desconhecido'),
            "autores": info_volume.get('authors', ['Desconhecido']),
            "descricao": info_volume.get('description', 'Descrição não disponível')
        })
    return jsonify(resultados)

# Favoritar livro e salvar no banco de dados
@app.route('/favoritar', methods=['POST'])
def favoritar_livro():
    try:
        dados = request.json
        id_google = dados.get('id_google')
        titulo = dados.get('titulo')
        autores = ', '.join(dados.get('autores', []))
        descricao = dados.get('descricao')

        if not id_google or not titulo:
            return jsonify({"erro": "Campos obrigatórios ausentes"}), 400

        conexao = conectar_banco()
        if conexao is None:
            return jsonify({"erro": "Erro ao conectar ao banco de dados"}), 500
        
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO favoritos (google_id, titulo, autores, descricao) VALUES (%s, %s, %s, %s)",
            (id_google, titulo, autores, descricao)
        ) 
        conexao.commit()

        cursor.close()
        conexao.close()

        return jsonify({"mensagem": "Livro favoritado com sucesso"})
    except Exception as e:
        print(f"Erro ao favoritar livro: {e}")
        return jsonify({"erro": "Erro interno no servidor"}), 500

# Rota para ver livros favoritados
@app.route('/favoritos', methods=['GET'])
def ver_favoritos():
    conexao = conectar_banco()
    if conexao is None:
        return jsonify({"erro": "Erro ao conectar ao banco de dados"}), 500

    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM favoritos")
    favoritos = cursor.fetchall()

    # Converter os dados em formato JSON amigável
    livros_favoritos = []
    for favorito in favoritos:
        livros_favoritos.append({
            "id": favorito[0],  # Ajuste conforme a estrutura da tabela
            "titulo": favorito[1],
            "autores": favorito[2]
        })

    cursor.close()
    conexao.close()

    return jsonify(livros_favoritos)


# Rota para remover livro dos favoritos
@app.route('/remover_favorito/<int:id>', methods=['DELETE'])
def remover_favorito(id):
    conexao = conectar_banco()
    if conexao is None:
        return jsonify({"erro": "Erro ao conectar ao banco de dados"}), 500
    
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM favoritos WHERE id = %s", (id,))
    conexao.commit()

    cursor.close()
    conexao.close()

    return jsonify({"mensagem": "Livro removido dos favoritos com sucesso"})

if __name__ == '__main__':
    app.run(debug=True)
