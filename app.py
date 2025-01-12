from flask import Flask, request, jsonify, render_template
import requests
import psycopg2
from psycopg2.extras import DictCursor
from config import DB_CONFIG, GOOGLE_BOOKS_API_URL

app = Flask(__name__)


# Conexão com o banco de dados
def conectar_banco():
    return psycopg2.connect(**DB_CONFIG)


# Rota para a página inicial (index)
@app.route('/')
def index():
    return render_template('index.html')  # Isso irá servir o arquivo index.html

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
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)


        cursor.execute(
        "INSERT INTO favoritos (google_id, titulo, autores, descricao) VALUES (%s, %s, %s, %s)",
        (id_google, titulo, autores, descricao)
        ) 


        conexao.commit()

        cursor.close()
        conexao.close()

        return jsonify({"mensagem": "Livro favoritado com sucesso"})
    except Exception as e:
        print(f"Erro ao favoritar livro: {e}")  # Exibe o erro no terminal
        return jsonify({"erro": "Erro interno no servidor"}), 500


# Rota para ver livros favoritados
@app.route('/favoritos', methods=['GET'])
def ver_favoritos():
    conexao = conectar_banco()
    cursor = conexao.cursor(cursor_factory=DictCursor)  # Usando o DictCursor aqui

    cursor.execute("SELECT * FROM favoritos")
    favoritos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(favoritos)


@app.route('/remover_favorito/<int:id>', methods=['DELETE'])
def remover_favorito(id):
    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("DELETE FROM favoritos WHERE id = %s", (id,))
    conexao.commit()

    cursor.close()
    conexao.close()

    return jsonify({"mensagem": "Livro removido dos favoritos com sucesso"})


if __name__ == '__main__':
    app.run(debug=True)
