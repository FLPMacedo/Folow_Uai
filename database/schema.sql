-- ============================================================================
-- FollowUai — Schema SQLite
-- Versão: 0.1 · MVP
-- Source: ../../3 modelo.banco.md (typos corrigidos)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- clientes
-- ============================================================================
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL,              -- formato internacional: +5531999999999
    email TEXT,
    data_nascimento DATE,
    data_inicio_parceria DATE NOT NULL,
    plano TEXT,
    grupo TEXT,
    status TEXT DEFAULT 'ativo',         -- 'ativo' | 'inativo'
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clientes_telefone ON clientes(telefone);
CREATE INDEX IF NOT EXISTS idx_clientes_status ON clientes(status);
CREATE INDEX IF NOT EXISTS idx_clientes_data_inicio ON clientes(data_inicio_parceria);

-- ============================================================================
-- telefones_whatsapp (multi-número, rotação anti-banimento)
-- ============================================================================
CREATE TABLE IF NOT EXISTS telefones_whatsapp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    instancia_evolution TEXT NOT NULL,
    nome_fantasia TEXT,
    status TEXT DEFAULT 'ativo',         -- 'ativo' | 'inativo' | 'bloqueado'
    ultimo_envio TIMESTAMP,
    total_envios INTEGER DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telefones_status ON telefones_whatsapp(status);

-- ============================================================================
-- templates
-- ============================================================================
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    modulo TEXT NOT NULL,                -- 'pos_venda' | 'evento' | 'comemorativo' | 'sumiu' | 'expiracao'
    tipo_gatilho TEXT NOT NULL,
    mensagem_texto TEXT NOT NULL,
    caminho_imagem TEXT,
    variaveis TEXT,                      -- JSON: ["nome","dias_parceria","plano"]
    ativo BOOLEAN DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_templates_modulo ON templates(modulo);

-- ============================================================================
-- campanhas
-- ============================================================================
CREATE TABLE IF NOT EXISTS campanhas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    modulo TEXT NOT NULL,
    template_id INTEGER NOT NULL,
    telefone_whatsapp_id INTEGER,        -- NULL = rotação automática
    data_inicio DATE,
    data_fim DATE,
    gatilho_data TEXT,                   -- 'data_compra' | 'data_evento' | 'aniversario' | 'dias_parceria' | 'expiracao'
    valor_gatilho INTEGER,               -- ex: 30 (dias), 100 (dias parceria)
    intervalo_minutos INTEGER DEFAULT 5,
    status TEXT DEFAULT 'ativo',         -- 'ativo' | 'pausado' | 'concluido'
    total_previsto INTEGER,
    total_enviados INTEGER DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES templates(id),
    FOREIGN KEY (telefone_whatsapp_id) REFERENCES telefones_whatsapp(id)
);

CREATE INDEX IF NOT EXISTS idx_campanhas_modulo ON campanhas(modulo);
CREATE INDEX IF NOT EXISTS idx_campanhas_status ON campanhas(status);

-- ============================================================================
-- envios
-- ============================================================================
CREATE TABLE IF NOT EXISTS envios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    telefone_whatsapp_id INTEGER,
    campanha_id INTEGER,
    template_id INTEGER,
    modulo TEXT NOT NULL,
    telefone_destino TEXT NOT NULL,
    mensagem_texto TEXT NOT NULL,
    imagem_path TEXT,
    status TEXT NOT NULL,                -- 'pendente' | 'enviado' | 'falha' | 'bloqueado'
    mensagem_evolution_id TEXT,          -- id retornado pela Evolution API
    erro TEXT,
    enviado_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (telefone_whatsapp_id) REFERENCES telefones_whatsapp(id),
    FOREIGN KEY (campanha_id) REFERENCES campanhas(id),
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

CREATE INDEX IF NOT EXISTS idx_envios_cliente ON envios(cliente_id);
CREATE INDEX IF NOT EXISTS idx_envios_status ON envios(status);
CREATE INDEX IF NOT EXISTS idx_envios_enviado_em ON envios(enviado_em);

-- ============================================================================
-- respostas (webhook receptivo Evolution)
-- ============================================================================
CREATE TABLE IF NOT EXISTS respostas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    telefone_origem TEXT NOT NULL,
    telefone_destino TEXT NOT NULL,
    mensagem_texto TEXT NOT NULL,
    tipo_mensagem TEXT,                  -- 'text' | 'image' | 'audio' | 'video' | 'document'
    mensagem_evolution_id TEXT,
    recebido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado BOOLEAN DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE INDEX IF NOT EXISTS idx_respostas_cliente ON respostas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_respostas_recebido_em ON respostas(recebido_em);

-- ============================================================================
-- eventos (pós-venda + pós-evento)
-- ============================================================================
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    nome_evento TEXT NOT NULL,
    tipo_evento TEXT NOT NULL,           -- 'pos_venda' | 'evento'
    data_evento DATE NOT NULL,
    data_compra DATE,                    -- usado para pós-venda
    vespera_mensagem_enviada BOOLEAN DEFAULT 0,
    pos_mensagem_enviada BOOLEAN DEFAULT 0,
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE INDEX IF NOT EXISTS idx_eventos_cliente ON eventos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_eventos_data ON eventos(data_evento);

-- ============================================================================
-- comemorativos (aniversário + marcos de parceria)
-- ============================================================================
CREATE TABLE IF NOT EXISTS comemorativos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,                  -- 'aniversario' | '100_dias' | '500_dias' | '1000_dias' | '6_meses' | '1_ano'
    data_gatilho DATE NOT NULL,
    dias_parceria INTEGER,
    mensagem_enviada BOOLEAN DEFAULT 0,
    imagem_enviada BOOLEAN DEFAULT 0,
    caminho_imagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE INDEX IF NOT EXISTS idx_comemorativos_cliente ON comemorativos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_comemorativos_data ON comemorativos(data_gatilho);

-- ============================================================================
-- planos (expiração 30/15/7/3)
-- ============================================================================
CREATE TABLE IF NOT EXISTS planos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    nome_plano TEXT NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    dias_restantes INTEGER,
    mensagem_30_dias_enviada BOOLEAN DEFAULT 0,
    mensagem_15_dias_enviada BOOLEAN DEFAULT 0,
    mensagem_7_dias_enviada BOOLEAN DEFAULT 0,
    mensagem_3_dias_enviada BOOLEAN DEFAULT 0,
    renova BOOLEAN DEFAULT 0,
    data_renovacao DATE,
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE INDEX IF NOT EXISTS idx_planos_cliente ON planos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_planos_data_fim ON planos(data_fim);

-- ============================================================================
-- tags + cliente_tags (M:N)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT,
    descricao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cliente_tags (
    cliente_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cliente_id, tag_id),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cliente_tags_cliente ON cliente_tags(cliente_id);
CREATE INDEX IF NOT EXISTS idx_cliente_tags_tag ON cliente_tags(tag_id);

-- ============================================================================
-- backups (histórico)
-- ============================================================================
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caminho_arquivo TEXT NOT NULL,
    tamanho_bytes INTEGER,
    descricao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- VIEW: v_clientes_ativos (com dias_parceria calculado)
-- ============================================================================
DROP VIEW IF EXISTS v_clientes_ativos;
CREATE VIEW v_clientes_ativos AS
SELECT
    id,
    nome,
    telefone,
    email,
    data_nascimento,
    data_inicio_parceria,
    plano,
    grupo,
    status,
    observacoes,
    CAST(julianday('now') - julianday(data_inicio_parceria) AS INTEGER) AS dias_parceria
FROM clientes
WHERE status = 'ativo';

-- ============================================================================
-- VIEW: v_envios_por_modulo (resumo para relatórios)
-- ============================================================================
DROP VIEW IF EXISTS v_envios_por_modulo;
CREATE VIEW v_envios_por_modulo AS
SELECT
    modulo,
    COUNT(*) AS total_envios,
    SUM(CASE WHEN status = 'enviado'   THEN 1 ELSE 0 END) AS enviados,
    SUM(CASE WHEN status = 'falha'     THEN 1 ELSE 0 END) AS falhas,
    SUM(CASE WHEN status = 'bloqueado' THEN 1 ELSE 0 END) AS bloqueados,
    SUM(CASE WHEN status = 'pendente'  THEN 1 ELSE 0 END) AS pendentes
FROM envios
GROUP BY modulo;

-- ============================================================================
-- SEEDS (templates padrão)
-- ============================================================================
INSERT INTO templates (nome, modulo, tipo_gatilho, mensagem_texto, variaveis, ativo)
SELECT 'Aniversário - Padrão', 'comemorativo', 'aniversario',
       'Feliz aniversário, {nome}! 🎉🎂' || char(10) || char(10) ||
       'Que este dia seja incrível como você!' || char(10) ||
       'Agradecemos pela parceria de {tempo_parceria}!',
       '["nome","tempo_parceria"]', 1
WHERE NOT EXISTS (SELECT 1 FROM templates WHERE nome = 'Aniversário - Padrão');

INSERT INTO templates (nome, modulo, tipo_gatilho, mensagem_texto, variaveis, ativo)
SELECT 'Expiração de Plano - 30 dias', 'expiracao', '30_dias',
       'Olá, {nome}! 👋' || char(10) || char(10) ||
       'Seu plano irá encerrar em 30 dias.' || char(10) ||
       'Você é muito especial para nós e seria importante termos você por mais um período!' || char(10) || char(10) ||
       'Renove com antecedência e ganhe BÔNUS + DESCONTO especial!' || char(10) || char(10) ||
       'Pode renovar até {dias_restantes} dias antes.',
       '["nome","dias_restantes"]', 1
WHERE NOT EXISTS (SELECT 1 FROM templates WHERE nome = 'Expiração de Plano - 30 dias');

INSERT INTO templates (nome, modulo, tipo_gatilho, mensagem_texto, variaveis, ativo)
SELECT 'Pós-Venda - Agradecimento', 'pos_venda', 'imediato',
       'Obrigado pela sua compra, {nome}! 🛒' || char(10) || char(10) ||
       'Esperamos que você goste muito do seu produto.' || char(10) ||
       'Qualquer dúvida, estamos aqui!',
       '["nome"]', 1
WHERE NOT EXISTS (SELECT 1 FROM templates WHERE nome = 'Pós-Venda - Agradecimento');

INSERT INTO templates (nome, modulo, tipo_gatilho, mensagem_texto, variaveis, ativo)
SELECT 'Sumiu Por Quê? - Reativação', 'sumiu', '30_dias_inativo',
       'Oi, {nome}! Sentimos sua falta aqui! 😢' || char(10) || char(10) ||
       'Já faz {dias_inativo} dias que não te vemos.' || char(10) ||
       'Queremos você de volta com 20% de desconto na próxima compra!' || char(10) || char(10) ||
       'Vem pro rolê!',
       '["nome","dias_inativo"]', 1
WHERE NOT EXISTS (SELECT 1 FROM templates WHERE nome = 'Sumiu Por Quê? - Reativação');

-- ============================================================================
-- negocios — multi-empresa (added v1.1)
-- Variáveis em templates: {empresa_nome}, {empresa_endereco},
-- {empresa_telefone}, {empresa_whatsapp}, {empresa_email}, {empresa_site}.
-- Apenas 1 com is_default=1 — backend mantém invariante.
-- ============================================================================
CREATE TABLE IF NOT EXISTS negocios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    endereco TEXT,
    telefone_contato TEXT,
    whatsapp_duvidas TEXT,
    email TEXT,
    site TEXT,
    descricao TEXT,
    is_default BOOLEAN DEFAULT 0,
    ativo BOOLEAN DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_negocios_ativo ON negocios(ativo);
CREATE INDEX IF NOT EXISTS idx_negocios_default ON negocios(is_default);

-- ============================================================================
-- planos_servicos — catálogo de planos/serviços do negócio
-- Cliente.plano (texto livre legado) vai ser linkado a um plano_servico_id
-- na etapa 4 do post-MVP roadmap.
-- ============================================================================
CREATE TABLE IF NOT EXISTS planos_servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    preco REAL,
    periodicidade TEXT,        -- 'mensal' | 'anual' | 'unico'
    duracao_dias INTEGER,       -- usado pra calcular data_fim do Plano
    ativo BOOLEAN DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_planos_servicos_ativo ON planos_servicos(ativo);

-- ============================================================================
-- grupos — categorias de clientes (diferente de tags: 1 cliente = 1 grupo)
-- ============================================================================
CREATE TABLE IF NOT EXISTS grupos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT,                   -- hex ex '#FF5733'
    descricao TEXT,
    ativo BOOLEAN DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_grupos_ativo ON grupos(ativo);

-- ============================================================================
-- cliente_modulos — opt-in M:N (cliente, modulo)
-- Comportamento legado: cliente SEM nenhuma entry = participa de todos
-- (clientes pré-migração não perdem dispatchs). Quando user cria a 1ª
-- entry para esse cliente, vira "explícito" e só os módulos ativos disparam.
-- ============================================================================
CREATE TABLE IF NOT EXISTS cliente_modulos (
    cliente_id INTEGER NOT NULL,
    modulo TEXT NOT NULL,
    ativo BOOLEAN DEFAULT 1,
    opt_in_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT,
    PRIMARY KEY (cliente_id, modulo),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cliente_modulos_modulo ON cliente_modulos(modulo, ativo);

-- ============================================================================
-- cliente_grupos — M:N cliente↔grupo (1 cliente pode estar em N grupos)
-- Compat: clientes.grupo_id continua como "grupo primário" legado.
-- Política: se cliente tem >=1 entry aqui, considera essas como TRUTH.
-- Senão, cai no grupo_id legado.
-- ============================================================================
CREATE TABLE IF NOT EXISTS cliente_grupos (
    cliente_id INTEGER NOT NULL,
    grupo_id INTEGER NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cliente_id, grupo_id),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cliente_grupos_grupo ON cliente_grupos(grupo_id);
