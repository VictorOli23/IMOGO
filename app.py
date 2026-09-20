import os
import streamlit as st
import google.generativeai as genai
from PIL import Image
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURAÇÃO INICIAL DA PÁGINA ---
st.set_page_config(page_title="Gerador Imobiliário IA", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

# Carrega as variáveis de ambiente
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://dcsdcvs_db_user:32384820Ca@cluster0.w4kupji.mongodb.net/gerador_imoveis_db?appName=Cluster0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- ADMINISTRADOR DINÂMICO (VIA VARIÁVEL DE AMBIENTE) ---
EMAIL_ADMIN = os.getenv("EMAIL_ADMIN", "") 

@st.cache_resource 
def init_connection():
    return MongoClient(MONGO_URI)

client = init_connection()
db = client.gerador_imoveis_db 
colecao_usuarios = db.usuarios 
colecao_historico = db.historico 

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- FUNÇÕES CORE ---
def formatar_imagem(imagem, formato):
    w, h = imagem.size
    if formato == "Instagram (Feed)":
        aspect_ratio = 1.0
    elif formato in ["Instagram (Stories)", "WhatsApp (Status)"]:
        aspect_ratio = 9/16
    elif formato == "Facebook (Post)":
        aspect_ratio = 1.91
    else:
        return imagem
    target_w = w
    target_h = int(w / aspect_ratio)
    if target_h > h:
        target_h = h
        target_w = int(h * aspect_ratio)
    left = (w - target_w) / 2
    top = (h - target_h) / 2
    right = (w + target_w) / 2
    bottom = (h + target_h) / 2
    return imagem.crop((left, top, right, bottom))

def cadastrar_usuario(email, senha):
    if colecao_usuarios.find_one({"email": email}):
        return False 
    senha_criptografada = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    colecao_usuarios.insert_one({"email": email, "senha_hash": senha_criptografada, "plano": "gratis", "anuncios_gerados": 0})
    return True

def fazer_login(email, senha):
    user = colecao_usuarios.find_one({"email": email})
    if user and bcrypt.checkpw(senha.encode('utf-8'), user['senha_hash']):
        return {"id": str(user['_id']), "plano": user['plano'], "uso": user['anuncios_gerados'], "email": user['email']}
    return None

def registrar_uso_e_historico(user_id, tipo_imovel, bairro, texto_gerado):
    colecao_usuarios.update_one({"_id": ObjectId(user_id)}, {"$inc": {"anuncios_gerados": 1}})
    st.session_state.usuario_logado['uso'] += 1
    
    colecao_historico.insert_one({
        "user_id": ObjectId(user_id),
        "data_criacao": datetime.now(),
        "tipo_imovel": tipo_imovel,
        "bairro": bairro,
        "texto": texto_gerado
    })

def alterar_plano_usuario(user_id, novo_plano):
    colecao_usuarios.update_one({"_id": ObjectId(user_id)}, {"$set": {"plano": novo_plano}})

# --- ESTADO DE SESSÃO ---
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

# --- CONTROLE DE TEMA (CLARO/ESCURO) ---
if 'tema_escuro' not in st.session_state:
    st.session_state.tema_escuro = False

def aplicar_tema():
    if st.session_state.tema_escuro:
        css = """
        <style>
            #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
            .stApp { background-color: #121212; color: #E0E0E0; }
            div[data-testid="stForm"] { background-color: #1E1E1E; border: 1px solid #333; border-radius: 12px; padding: 24px; }
            .stButton>button { background: linear-gradient(90deg, #FF4B4B 0%, #FF7676 100%); color: white; border: none; border-radius: 8px; width: 100%; font-weight: bold; }
            .stButton>button:hover { transform: translateY(-2px); }
        </style>
        """
    else:
        css = """
        <style>
            #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
            .stApp { background-color: #F8F9FA; color: #212529; }
            div[data-testid="stForm"] { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .stButton>button { background: linear-gradient(90deg, #FF4B4B 0%, #FF7676 100%); color: white; border: none; border-radius: 8px; width: 100%; font-weight: bold; }
            .stButton>button:hover { transform: translateY(-2px); }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

aplicar_tema()

# --- ECRÃ DE LOGIN E REGISTO ---
if not st.session_state.usuario_logado:
    st.title("✨ Copywriter Imobiliário IA")
    st.markdown("A sua agência de marketing no bolso. Faça login para continuar.")
    st.write("") 
    
    tab1, tab2 = st.tabs(["Entrar na Conta", "Criar Conta Grátis"])
    
    with tab1:
        email_login = st.text_input("E-mail", key="login_email")
        senha_login = st.text_input("Palavra-passe", type="password", key="login_senha")
        if st.button("Aceder ao Painel", type="primary"):
            usuario = fazer_login(email_login, senha_login)
            if usuario:
                st.session_state.usuario_logado = usuario
                st.rerun()
            else:
                st.error("⚠️ Credenciais incorretas.")
                
    with tab2:
        email_cad = st.text_input("E-mail", key="cad_email")
        senha_cad = st.text_input("Palavra-passe", type="password", key="cad_senha")
        if st.button("Registar Agora"):
            if cadastrar_usuario(email_cad, senha_cad):
                st.success("✅ Conta criada com sucesso! Faça login ao lado.")
            else:
                st.error("⚠️ Este e-mail já existe.")

# --- ECRÃ PRINCIPAL (ÁREA PRIVADA) ---
else:
    user = st.session_state.usuario_logado
    
    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        tema_selecionado = st.toggle("🌙 Modo Escuro", value=st.session_state.tema_escuro)
        if tema_selecionado != st.session_state.tema_escuro:
            st.session_state.tema_escuro = tema_selecionado
            st.rerun()
            
        st.divider()
        st.markdown("## 👤 Meu Perfil")
        st.markdown(f"**{user['email']}**")
        
        plano_formatado = "👑 PRO" if user['plano'] == 'pro' else "🆓 GRÁTIS"
        st.markdown(f"### Plano Atual: {plano_formatado}")
        
        if user['plano'] == 'gratis':
            progresso = user['uso'] / 2.0
            st.progress(progresso)
            st.caption(f"Utilizou {user['uso']} de 2 anúncios neste mês.")
            st.button("🚀 Fazer Upgrade para PRO", type="primary", use_container_width=True)
        else:
            st.success("Acesso Ilimitado Ativo")
            
        st.divider()
        if st.button("🚪 Terminar Sessão", use_container_width=True):
            st.session_state.usuario_logado = None
            st.rerun()
            
    # --- PAINEL DE ADMINISTRADOR EXCLUSIVO (Verifica de forma segura) ---
    if EMAIL_ADMIN and user['email'] == EMAIL_ADMIN:
        with st.expander("👑 PAINEL DE GESTÃO DO SAAS", expanded=False):
            st.markdown("Controlo de Utilizadores")
            todos_clientes = list(colecao_usuarios.find())
            
            for cliente in todos_clientes:
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.write(cliente['email'])
                c2.write("⭐ PRO" if cliente['plano'] == 'pro' else "Grátis")
                c3.write(str(cliente['anuncios_gerados']))
                
                if cliente['plano'] == 'gratis':
                    if c4.button("Dar PRO", key=f"up_{cliente['_id']}"):
                        alterar_plano_usuario(cliente['_id'], "pro")
                        st.rerun()
                else:
                    if c4.button("Remover", key=f"down_{cliente['_id']}"):
                        alterar_plano_usuario(cliente['_id'], "gratis")
                        st.rerun()
                        
    # --- NAVEGAÇÃO PRINCIPAL (ABAS) ---
    st.title("🏠 Máquina de Vendas Imobiliárias")
    
    aba_gerador, aba_historico = st.tabs(["✨ Criar Novo Anúncio", "🗂️ Meu Histórico de Postagens"])
    
    with aba_gerador:
        limite_atingido = user['plano'] == 'gratis' and user['uso'] >= 2

        if limite_atingido:
            st.error("🔒 Atingiu o limite de publicações do plano Gratuito.")
            st.info("Faça o upgrade para o plano PRO para gerar anúncios ilimitados.")
        else:
            with st.container():
                with st.form("imovel_form"):
                    st.markdown("### 📋 Informações do Imóvel")
                    col1, col2 = st.columns(2)
                    with col1:
                        tipo = st.selectbox("Tipo de Imóvel", ["Apartamento", "Moradia", "Terreno", "Espaço Comercial", "Imóvel de Luxo"])
                        bairro = st.text_input("Localização (Zona/Bairro)", placeholder="Ex: Parque das Nações")
                        diferenciais = st.text_area("Principais Diferenciais", placeholder="Ex: 3 suítes, varanda com churrasqueira...", height=110)
                    
                    with col2:
                        tom_venda = st.selectbox("Tom da Publicação", ["Emocional (Família)", "Investidor (Rentabilidade)", "Luxo (Exclusividade)"])
                        redes_sociais = st.multiselect(
                            "Onde deseja publicar?", 
                            ["Instagram (Feed)", "Instagram (Stories)", "WhatsApp (Status)", "WhatsApp (Mensagem)", "Facebook (Post)", "Portal"],
                            default=["Instagram (Feed)", "WhatsApp (Mensagem)"]
                        )
                        st.markdown("### 📸 Fotografias")
                        arquivos_fotos = st.file_uploader("A IA analisará a luz e os acabamentos", accept_multiple_files=True, type=["png", "jpg", "jpeg"])

                    submit = st.form_submit_button("Gerar Material Completo 🚀")

            if submit:
                if not GEMINI_API_KEY:
                    st.error("⚠️ Falha: Chave da API Gemini não configurada.")
                elif not arquivos_fotos:
                    st.warning("⚠️ Adicione pelo menos uma fotografia para ativar a análise visual.")
                elif not redes_sociais:
                    st.warning("⚠️ Selecione pelo menos uma plataforma.")
                else:
                    imagens_pil = [Image.open(foto) for foto in arquivos_fotos]
                    model = genai.GenerativeModel('gemini-1.5-flash') 

                    prompt = f"""
                    Atue como copywriter imobiliário. Analise as fotografias deste imóvel ({tipo}) em {bairro}.
                    Diferenciais: {diferenciais}. Tom: {tom_venda}.
                    ANÁLISE VISUAL: Descreva os acabamentos e a luz natural que observa nas imagens.
                    Escreva publicações para: {', '.join(redes_sociais)}.
                    """

                    with st.spinner("🧠 A IA está a redigir os textos..."):
                        try:
                            conteudo_ia = [prompt] + imagens_pil
                            response = model.generate_content(conteudo_ia)
                            
                            registrar_uso_e_historico(user["id"], tipo, bairro, response.text)
                            
                            st.success("✅ O seu material de marketing está pronto!")
                            st.markdown("### 📝 Textos Otimizados")
                            st.markdown(response.text)
                            
                            st.markdown("### 🖼️ Imagens Cortadas")
                            for rede in redes_sociais:
                                if rede in ["Instagram (Feed)", "Instagram (Stories)", "Facebook (Post)", "WhatsApp (Status)"]:
                                    st.subheader(f"Formato: {rede}")
                                    img_formatada = formatar_imagem(imagens_pil[0], rede)
                                    st.image(img_formatada, use_column_width=True)
                            
                        except Exception as e:
                            st.error(f"Ocorreu um erro: {e}")

    with aba_historico:
        st.markdown("### 🗂️ Publicações Anteriores")
        st.caption("Todos os textos gerados pela IA ficam guardados aqui para copiar e colar quando precisar.")
        
        meu_historico = list(colecao_historico.find({"user_id": ObjectId(user['id'])}).sort("data_criacao", -1))
        
        if not meu_historico:
            st.info("Ainda não gerou nenhum anúncio. Use a aba ao lado para criar o seu primeiro!")
        else:
            for item in meu_historico:
                data_str = item['data_criacao'].strftime("%d/%m/%Y às %H:%M")
                titulo_expander = f"{item.get('tipo_imovel', 'Imóvel')} em {item.get('bairro', 'Local Não Informado')} - {data_str}"
                
                with st.expander(titulo_expander):
                    st.markdown(item.get('texto', 'Texto não encontrado.'))