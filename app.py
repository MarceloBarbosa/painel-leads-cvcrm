import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página para visual moderno e amplo
st.set_page_config(page_title="Inteligência de Leads - CV CRM", layout="wide", initial_sidebar_state="expanded")

# Estilização CSS para um visual Dark Mode Premium / Minimalista
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stMetric"] { background-color: #1f293d; padding: 15px; border-radius: 10px; border: 1px solid #2d3748; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Painel de Inteligência Comercial (CV CRM & WhatsApp)")
st.caption("Análise em tempo real de gargalos de funil e ações de vendas prioritárias.")

# 1. Base de dados simulada (Estrutura exata do seu funil)
dados_leads = [
    {"nome": "Carlos Silva", "etiqueta": "Cliente Qualificado", "tempo_sem_res": 2, "proximo_passo": "Enviar contrato de compra e venda", "msg": "Olá Carlos, a simulação aprovou! Segue o link com os documentos do contrato para assinatura..."},
    {"nome": "Mariana Costa", "etiqueta": "Simulação", "tempo_sem_res": 26, "proximo_passo": "Cobrar envio da certidão de nascimento", "msg": "Oi Mariana, consegui rodar aquela simulação que combinamos. Ficou excelente! Consegue me mandar a certidão para eu juntar na pasta?"},
    {"nome": "Roberto Souza", "etiqueta": "Filtro", "tempo_sem_res": 5, "proximo_passo": "Descobrir região de preferência e renda", "msg": "Tudo bem, Roberto? Para eu te mandar as melhores opções, qual região você prefere e qual a média de renda que pretende usar?"},
    {"nome": "Amanda Lima", "etiqueta": "Em Atendimento", "tempo_sem_res": 1, "proximo_passo": "Montar proposta para a construtora", "msg": "Oi Amanda, já estou montando a sua proposta com o fluxo de tabela que conversamos!"},
    {"nome": "Ricardo Alves", "etiqueta": "1ª Tratativa", "tempo_sem_res": 48, "proximo_passo": "Disparar 2ª Tratativa", "msg": "Olá Ricardo, vi que demonstrou interesse no residencial. Chegou a ver as fotos que te mandei?"}
]
df = pd.DataFrame(dados_leads)

# Distribuição fixa para preencher o gráfico de funil completo
funil_ordem = ["1ª Tratativa", "2ª Tratativa", "3ª Tratativa", "Em Atendimento", "Filtro", "Simulação", "Documentos", "Proposta", "Cliente Qualificado"]
contagem_etiquetas = {"1ª Tratativa": 12, "2ª Tratativa": 8, "3ª Tratativa": 4, "Em Atendimento": 15, "Filtro": 9, "Simulação": 7, "Documentos": 5, "Proposta": 3, "Cliente Qualificado": 4}
df_funil = pd.DataFrame([{"Etapa": k, "Quantidade": v} for k, v in contagem_etiquetas.items()])

# 2. Linha superior com KPIs rápidos
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total de Leads Ativos", sum(contagem_etiquetas.values()))
with col2:
    st.metric("Clientes Qualificados", contagem_etiquetas["Cliente Qualificado"])
with col3:
    st.metric("Taxa de Resposta (Engajamento)", "68%", delta="WhatsApp Ativo")
with col4:
    leads_travados = len(df[df["tempo_sem_res"] >= 24])
    st.metric("Alertas de Follow-up (>24h)", f"{leads_travados} leads", delta="- Alerta crítico", delta_color="inverse")

st.write("---")

# 3. Gráfico do Funil Imobiliário
st.subheader("📌 Onde estão seus clientes? (Gargalo do Funil)")
fig = px.bar(df_funil, x="Quantidade", y="Etapa", orientation="h",
             category_orders={"Etapa": funil_ordem[::-1]},
             color="Quantidade", color_continuous_scale="Blues")
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#ffffff",
                  height=350, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig)

st.write("---")

# 4. Últimos leads analisados
st.subheader("🗂️ Últimos leads analisados")
st.dataframe(
    df[["nome", "etiqueta", "tempo_sem_res", "proximo_passo"]].rename(columns={
        "nome": "Lead", "etiqueta": "Etiqueta", "tempo_sem_res": "Horas sem resposta", "proximo_passo": "Próximo passo"}),
    hide_index=True,
)

st.write("---")

# 5. Painel Operacional: Ações Rápidas para o Corretor
st.subheader("⚡ Painel de Ação de Vendas (Copiar e Enviar)")
st.caption("Use o ícone de copiar no canto do quadro da mensagem para levá-la ao WhatsApp.")
for index, row in df.iterrows():
    col_info, col_acao = st.columns([2, 3])

    with col_info:
        cor_tag = "🔴 Alerta: Travado" if row["tempo_sem_res"] >= 24 else "🟢 Ativo"
        st.markdown(f"### **{row['nome']}**")
        st.markdown(f"**Etiqueta:** `{row['etiqueta']}` | **Status:** {cor_tag}")
        st.markdown(f"**Próximo Passo:** *{row['proximo_passo']}*")

    with col_acao:
        st.markdown("Sugestão de Mensagem de Vendas (Gerada pela IA):")
        st.code(row["msg"], language=None, wrap_lines=True)
    st.markdown("<hr style='border-top: 1px dashed #2d3748;'>", unsafe_allow_html=True)
