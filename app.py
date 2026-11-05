import unicodedata
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Inteligência de Leads - CV CRM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    div[data-testid="stMetric"] { background-color: #1f293d; padding: 15px; border-radius: 10px; border: 1px solid #2d3748; }
    </style>
""", unsafe_allow_html=True)

FUNIL = ["1ª Tratativa", "2ª Tratativa", "3ª Tratativa", "Em Atendimento", "Filtro",
         "Simulação", "Documentos", "Proposta", "Cliente Qualificado"]

PROXIMO_PASSO = {
    "1ª Tratativa": "Disparar 2ª Tratativa",
    "2ª Tratativa": "Disparar 3ª Tratativa",
    "3ª Tratativa": "Última tentativa: ligação + áudio no WhatsApp",
    "Em Atendimento": "Iniciar filtro: região, renda e momento de compra",
    "Filtro": "Rodar a simulação com a renda informada",
    "Simulação": "Solicitar documentos para análise de crédito",
    "Documentos": "Conferir documentos e montar a proposta",
    "Proposta": "Acompanhar retorno da construtora e negociar",
    "Cliente Qualificado": "Enviar contrato e agendar assinatura",
}

MENSAGEM = {
    "1ª Tratativa": "Olá {nome}, tudo bem? Vi seu interesse no empreendimento e separei algumas opções para você. Posso te mandar?",
    "2ª Tratativa": "Oi {nome}! Passando para saber se conseguiu ver as informações que te enviei. Quer que eu te mande fotos e valores?",
    "3ª Tratativa": "{nome}, não quero ser insistente 😊 Se ainda fizer sentido para você, me responde aqui que te passo as condições atualizadas.",
    "Em Atendimento": "Que bom falar com você, {nome}! Para eu te indicar as melhores opções, qual região você prefere?",
    "Filtro": "{nome}, com essas informações já consigo rodar uma simulação para você. Qual a renda que pretende usar?",
    "Simulação": "Oi {nome}, a simulação ficou ótima! Consegue me mandar RG, CPF e comprovante de renda para eu seguir com a análise?",
    "Documentos": "{nome}, recebi seus documentos! Já estou montando sua proposta e te aviso assim que sair.",
    "Proposta": "Oi {nome}, sua proposta já está com a construtora. Assim que tiver retorno te chamo aqui!",
    "Cliente Qualificado": "Parabéns, {nome}! Tudo aprovado. Vamos agendar a assinatura do contrato?",
}


def _norm(txt):
    txt = unicodedata.normalize("NFKD", str(txt or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(txt.split())


def mapear_etapa(situacao):
    """Converte o nome da situação do CV CRM para uma etapa do funil."""
    s = _norm(situacao)
    if "qualific" in s:
        return "Cliente Qualificado"
    if "proposta" in s:
        return "Proposta"
    if "document" in s:
        return "Documentos"
    if "simula" in s:
        return "Simulação"
    if "filtro" in s:
        return "Filtro"
    if "atendimento" in s:
        return "Em Atendimento"
    if "3" in s and "tratativa" in s:
        return "3ª Tratativa"
    if "2" in s and "tratativa" in s:
        return "2ª Tratativa"
    if "tratativa" in s or "novo" in s or "aguardando" in s:
        return "1ª Tratativa"
    return None


def _pegar(d, *chaves):
    for c in chaves:
        v = d.get(c)
        if isinstance(v, dict):
            v = v.get("nome") or v.get("situacao") or v.get("titulo")
        if v not in (None, ""):
            return v
    return None


@st.cache_data(ttl=600, show_spinner="Buscando leads no CV CRM...")
def buscar_leads(dominio, email, token):
    url = f"https://{dominio}.cvcrm.com.br/api/v1/comercial/leads"
    headers = {"email": email, "token": token, "accept": "application/json"}
    todos, offset, limite = [], 0, 100
    for _ in range(50):  # até 5.000 leads
        r = requests.get(url, headers=headers, params={"limit": limite, "offset": offset, "ativo": "S"}, timeout=30)
        r.raise_for_status()
        dados = r.json()
        if isinstance(dados, dict):
            lote = dados.get("leads") or dados.get("dados") or dados.get("data") or []
        else:
            lote = dados
        if not lote:
            break
        todos.extend(lote)
        if len(lote) < limite:
            break
        offset += limite
    return todos


def montar_df(brutos):
    agora = datetime.now()
    linhas = []
    for l in brutos:
        situacao = _pegar(l, "situacao", "nome_situacao", "situacao_nome")
        ultima = _pegar(l, "data_ultima_interacao", "ultima_interacao", "data_ultima_alteracao",
                        "data_alteracao", "data_atualizacao", "data_cad", "data_cadastro")
        dt = pd.to_datetime(ultima, errors="coerce", dayfirst=False)
        horas = round((agora - dt.to_pydatetime().replace(tzinfo=None)).total_seconds() / 3600) if pd.notna(dt) else None
        linhas.append({
            "id": _pegar(l, "idlead", "id"),
            "nome": _pegar(l, "nome") or "Sem nome",
            "telefone": _pegar(l, "telefone", "celular"),
            "situacao_cv": situacao or "—",
            "etiqueta": mapear_etapa(situacao),
            "corretor": _pegar(l, "corretor", "nome_corretor"),
            "ultima_atividade": dt,
            "tempo_sem_res": horas,
        })
    return pd.DataFrame(linhas)


def dados_demo():
    base = [
        ("Carlos Silva", "Cliente Qualificado", 2), ("Mariana Costa", "Simulação", 26),
        ("Roberto Souza", "Filtro", 5), ("Amanda Lima", "Em Atendimento", 1), ("Ricardo Alves", "1ª Tratativa", 48),
    ]
    return pd.DataFrame([{"id": i, "nome": n, "telefone": None, "situacao_cv": e, "etiqueta": e, "corretor": None,
                          "ultima_atividade": pd.NaT, "tempo_sem_res": h} for i, (n, e, h) in enumerate(base)])


# ---------------- Fonte de dados ----------------
with st.sidebar:
    st.header("⚙️ Fonte de dados")
    try:
        cfg = dict(st.secrets.get("cvcrm", {}))
    except Exception:
        cfg = {}
    tem_api = all(cfg.get(k) for k in ("dominio", "email", "token"))
    opcoes = (["API do CV CRM"] if tem_api else []) + ["Planilha exportada do CV CRM", "Dados de demonstração"]
    fonte = st.radio("Origem dos leads", opcoes)
    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()

df, aviso = None, None
if fonte == "API do CV CRM":
    try:
        df = montar_df(buscar_leads(str(cfg["dominio"]).strip(), str(cfg["email"]).strip(), str(cfg["token"]).strip()))
        if df.empty:
            aviso = "A API respondeu, mas não retornou nenhum lead ativo."
    except requests.HTTPError as e:
        resposta = (e.response.text or "").strip()[:300]
        aviso = (f"O CV CRM recusou a requisição ({e.response.status_code}). Confira e-mail, token e domínio nos Secrets.\n\n"
                 f"Resposta do CV CRM: {resposta or '(vazia)'}\n\n"
                 f"Token lido dos Secrets com {len(str(cfg['token']).strip())} caracteres.")
    except Exception as e:
        aviso = f"Não consegui falar com o CV CRM: {e}"
elif fonte == "Planilha exportada do CV CRM":
    arq = st.sidebar.file_uploader("Envie o .xlsx ou .csv exportado da lista de leads", type=["xlsx", "csv"])
    if arq:
        bruto = pd.read_csv(arq, sep=None, engine="python") if arq.name.endswith(".csv") else pd.read_excel(arq)
        bruto.columns = [_norm(c).replace(" ", "_") for c in bruto.columns]
        df = montar_df(bruto.to_dict("records"))
    else:
        st.info("Exporte a lista de leads no CV CRM e envie o arquivo na barra lateral.")
        st.stop()
else:
    df = dados_demo()

if aviso:
    st.error(aviso)
    st.stop()

nao_mapeados = df[df["etiqueta"].isna()]
df = df[df["etiqueta"].notna()].copy()

# ---------------- Cabeçalho e KPIs ----------------
st.title("📊 Painel de Inteligência Comercial (CV CRM & WhatsApp)")
st.caption(f"Fonte: {fonte} · {len(df)} leads no funil · atualizado {datetime.now():%d/%m %H:%M}")

contagem = df["etiqueta"].value_counts().reindex(FUNIL, fill_value=0)
tratativas = contagem[["1ª Tratativa", "2ª Tratativa", "3ª Tratativa"]].sum()
responderam = contagem.sum() - tratativas
taxa = (responderam / contagem.sum() * 100) if contagem.sum() else 0
travados = df[df["tempo_sem_res"].fillna(0) >= 24]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Leads Ativos", int(contagem.sum()))
c2.metric("Clientes Qualificados", int(contagem["Cliente Qualificado"]))
c3.metric("Taxa de Resposta", f"{taxa:.0f}%", help="Leads que saíram das Tratativas e chegaram a Em Atendimento ou além.")
c4.metric("Alertas de Follow-up (>24h)", f"{len(travados)} leads",
          delta="Atenção" if len(travados) else None, delta_color="inverse")

st.write("---")

# ---------------- Funil ----------------
st.subheader("📌 Onde estão seus clientes? (Gargalo do Funil)")
df_funil = contagem.reset_index()
df_funil.columns = ["Etapa", "Quantidade"]
fig = px.bar(df_funil, x="Quantidade", y="Etapa", orientation="h",
             category_orders={"Etapa": FUNIL}, color="Quantidade", color_continuous_scale="Blues")
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#ffffff",
                  height=380, margin=dict(l=20, r=20, t=20, b=20), coloraxis_showscale=False)
st.plotly_chart(fig)

if len(nao_mapeados):
    with st.expander(f"⚠️ {len(nao_mapeados)} leads com situação que não reconheci no funil"):
        st.write("Situações encontradas:", ", ".join(sorted(nao_mapeados["situacao_cv"].astype(str).unique())))

st.write("---")

# ---------------- Tabela ----------------
st.subheader("🗂️ Últimos leads analisados")
tabela = df.sort_values("ultima_atividade", ascending=False, na_position="last")
st.dataframe(
    tabela[["nome", "etiqueta", "situacao_cv", "corretor", "tempo_sem_res"]].rename(columns={
        "nome": "Lead", "etiqueta": "Etiqueta", "situacao_cv": "Situação no CV",
        "corretor": "Corretor", "tempo_sem_res": "Horas sem atividade"}).head(50),
    hide_index=True,
)

st.write("---")

# ---------------- Ações ----------------
st.subheader("⚡ Painel de Ação de Vendas (Copiar e Enviar)")
st.caption("Prioridade para leads travados há mais de 24h. Use o ícone de copiar no canto da mensagem.")
fila = pd.concat([travados.sort_values("tempo_sem_res", ascending=False), df.drop(travados.index)]).head(15)
for idx, row in fila.iterrows():
    col_info, col_acao = st.columns([2, 3])
    primeiro_nome = str(row["nome"]).split()[0].title()
    with col_info:
        h = row["tempo_sem_res"]
        status = f"🔴 Travado há {int(h)}h" if pd.notna(h) and h >= 24 else "🟢 Ativo"
        st.markdown(f"### **{row['nome']}**")
        st.markdown(f"**Etiqueta:** `{row['etiqueta']}` | **Status:** {status}")
        st.markdown(f"**Próximo Passo:** *{PROXIMO_PASSO[row['etiqueta']]}*")
    with col_acao:
        st.markdown("Sugestão de mensagem:")
        st.code(MENSAGEM[row["etiqueta"]].format(nome=primeiro_nome), language=None, wrap_lines=True)
    st.markdown("<hr style='border-top: 1px dashed #2d3748;'>", unsafe_allow_html=True)
