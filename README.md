# SuperApp Finanças — MVP Streamlit

Este repositório contém uma versão inicial (MVP) do SuperApp Finanças construída com Streamlit.

Objetivo desta versão:
- Exibir uma tela inicial sem erros no Streamlit
- Mostrar o título "SuperApp Finanças"
- Exibir uma tabela de carteira de investimentos de exemplo
- Calcular e exibir o patrimônio total

Pré-requisitos
- Python 3.8+
- pip

Instalação e execução local
1. Clone este repositório e entre na branch mvp/skeleton:

   git clone https://github.com/mec4tronico/superapp_financas.git
   cd superapp_financas
   git checkout mvp/skeleton

2. (opcional) Crie e ative um ambiente virtual:

   python -m venv .venv
   # Linux / macOS
   source .venv/bin/activate
   # Windows PowerShell
   .venv\Scripts\Activate.ps1

3. Instale dependências:

   pip install -r requirements.txt

4. Rode a aplicação:

   streamlit run app.py

A página abrirá em http://localhost:8501 por padrão.

Publicar no Streamlit Cloud (GitHub)
1. Suba seu código para um repositório no GitHub (já está no repositório mec4tronico/superapp_financas na branch mvp/skeleton).
2. Acesse https://share.streamlit.io e faça login com sua conta GitHub.
3. Clique em "New app" → conecte o repositório → selecione a branch (mvp/skeleton) e o arquivo de entrada (app.py).
4. Clique em "Deploy". O Streamlit Cloud fará o build e disponibilizará a URL pública da sua aplicação.

Observações
- Este MVP usa dados de exemplo em memória. Em próximas entregas implementaremos o importador CSV da B3 e integração com uma camada de persistência.
- Se o repositório for privado, você precisará autorizar o Streamlit Cloud a acessar seus repositórios GitHub.
