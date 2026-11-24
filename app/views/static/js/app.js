// ============================================================
//  SFM — Sistema de Fiscalização Minerária
//  app.js — Frontend Operacional e Cartografia Leaflet
//  Padrão MVC puro · Zero frameworks externos
// ============================================================

const Estado = {
    pagina: 0,
    limite: 25,
    total: 0,
    termo: "",
    fase: "",
    titular: "",
    substancia: "",
    processo: "",
    apenasParauapebas: true,
    mapa: null,
    camadasBase: {},
    baseAtiva: "padrao",
    camadaLimite: null,
    camadaProcessos: null,
    poligonosMap: new Map(),
    linhaAtiva: null,
};

// ============================================================
//  UTILITÁRIOS
// ============================================================

function escaparHtml(str) {
    if (str === null || str === undefined) return "—";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

async function buscarJson(url, opcoes = {}) {
    const resposta = await fetch(url, opcoes);
    const dados = await resposta.json();
    if (!resposta.ok) {
        throw new Error(dados.mensagem || `Erro HTTP ${resposta.status}`);
    }
    return dados;
}

function formatarNumero(valor, casas = 2) {
    if (valor === null || valor === undefined || isNaN(valor)) return "—";
    return Number(valor).toLocaleString("pt-BR", {
        minimumFractionDigits: casas,
        maximumFractionDigits: casas,
    });
}

// ============================================================
//  STATUS DO BANCO DE DADOS
// ============================================================

async function atualizarStatusBanco() {
    const badge = document.getElementById("badge-banco");
    if (!badge) return;
    try {
        const dados = await buscarJson("/api/status");
        badge.textContent = `PostGIS: Ativo (${dados.banco})`;
        badge.className = "tag tag-status";
    } catch {
        badge.textContent = "PostGIS: Indisponível";
        badge.style.backgroundColor = "#7F1D1D";
        badge.style.color = "#FECACA";
    }
}

// ============================================================
//  CARREGAMENTO DE INDICADORES (KPIS)
// ============================================================

async function atualizarIndicadores() {
    try {
        const dados = await buscarJson("/api/resumo");
        const mun  = dados.municipio    || {};
        const est  = dados.estadual     || {};
        const fisc = dados.fiscalizacao || {};

        const elPaTotal   = document.getElementById("kpi-pa-total");
        const elPaValidas = document.getElementById("kpi-pa-validas");
        if (elPaTotal)   elPaTotal.textContent   = (est.total_processos || 0).toLocaleString("pt-BR");
        if (elPaValidas) elPaValidas.textContent = `Geometrias válidas: ${(est.geometrias_validas || 0).toLocaleString("pt-BR")}`;

        const elMunProc  = document.getElementById("kpi-mun-processos");
        const elMunFases = document.getElementById("kpi-mun-fases");
        if (elMunProc)  elMunProc.textContent  = (mun.total_processos || 0).toLocaleString("pt-BR");
        if (elMunFases) elMunFases.textContent = `Fases administrativas: ${mun.fases_distintas || 0} distintas`;

        const areaUnica    = mun.area_unica_ha       || 0;
        const areaRecortada= mun.soma_area_recortada_ha || 0;
        const areaMun      = mun.area_municipio_ha   || 688586.5;
        const cobertura    = areaMun > 0 ? ((areaUnica / areaMun) * 100).toFixed(2) : "0.00";

        const elArea       = document.getElementById("kpi-mun-area-ha");
        const elAreaDet    = document.getElementById("kpi-mun-area-detalhe");
        if (elArea)    elArea.textContent    = `${formatarNumero(areaUnica)} ha`;
        if (elAreaDet) elAreaDet.textContent = `Área única · Soma total: ${formatarNumero(areaRecortada)} ha (${cobertura}% do mun.)`;

        const statusMapBiomas = document.getElementById("kpi-mapbiomas-status");
        if (statusMapBiomas) {
            if (fisc.mapbiomas_integrado) {
                statusMapBiomas.textContent = "Integrado";
                statusMapBiomas.className   = "kpi-number text-emerald";
            } else {
                statusMapBiomas.textContent = "Aguardando Dados";
                statusMapBiomas.className   = "kpi-number text-amber";
            }
        }
    } catch (erro) {
        console.error("Falha ao carregar indicadores:", erro);
    }
}

// ============================================================
//  FILTRO DE FASES ADMINISTRATIVAS
// ============================================================

async function carregarFiltroFases() {
    try {
        const fases  = await buscarJson("/api/fases?apenas_parauapebas=true");
        const select = document.getElementById("campo-fase");
        if (!select) return;
        select.innerHTML = '<option value="">Todas as fases</option>';
        for (const f of fases) {
            const opt = document.createElement("option");
            opt.value       = f.fase;
            opt.textContent = `${f.fase} (${f.total})`;
            select.appendChild(opt);
        }
    } catch (erro) {
        console.error("Falha ao carregar fases:", erro);
    }
}

// ============================================================
//  MAPA CARTOGRÁFICO LEAFLET & CAMADAS BASE
// ============================================================

function inicializarMapa() {
    if (typeof L === "undefined") {
        const sub = document.getElementById("map-subtitle");
        if (sub) sub.textContent = "Biblioteca Leaflet não carregada.";
        return;
    }

    Estado.mapa = L.map("map", {
        center: [-6.067, -49.905],
        zoom: 9,
        zoomControl: true,
    });

    // 1. Definição das Camadas de Fundo (Basemaps)
    // Mapa Convencional (OpenStreetMap)
    const camadaPadrao = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        maxZoom: 19,
    });

    // Imagens de Satélite de Alta Resolução (Esri World Imagery)
    const camadaSatelite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: 'Imagens &copy; <a href="https://www.esri.com" target="_blank" rel="noopener">Esri</a>, USGS, Maxar, Earthstar Geographics',
        maxZoom: 19,
    });

    // Rótulos e Referências Geográficas para modo Híbrido (Esri World Boundaries and Places)
    const camadaRotulos = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
        attribution: '',
        maxZoom: 19,
        pane: 'overlayPane',
    });

    Estado.camadasBase = {
        padrao: camadaPadrao,
        satelite: camadaSatelite,
        rotulos: camadaRotulos,
    };

    // Adiciona a camada padrão inicial ao fundo
    Estado.camadasBase.padrao.addTo(Estado.mapa);
    Estado.baseAtiva = "padrao";

    // 2. Controle Visual no Canto Superior Direito com Ícones [ Mapa ] [ Satélite ] [ Híbrido ]
    const ControleBasemap = L.Control.extend({
        options: { position: "topright" },
        onAdd: function() {
            const container = L.DomUtil.create("div", "leaflet-bar basemap-switcher");
            container.innerHTML = `
                <button type="button" class="btn-basemap active" data-base="padrao" title="Mapa Cartográfico Convencional (OpenStreetMap)">
                    <svg class="basemap-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon><line x1="8" y1="2" x2="8" y2="18"></line><line x1="16" y1="6" x2="16" y2="22"></line></svg>
                    <span>Mapa</span>
                </button>
                <button type="button" class="btn-basemap" data-base="satelite" title="Imagem de Satélite de Alta Resolução (Esri World Imagery)">
                    <svg class="basemap-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                    <span>Satélite</span>
                </button>
                <button type="button" class="btn-basemap" data-base="hibrido" title="Satélite com Rótulos e Vias Urbanas">
                    <svg class="basemap-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
                    <span>Híbrido</span>
                </button>
            `;
            L.DomEvent.disableClickPropagation(container);
            L.DomEvent.disableScrollPropagation(container);

            container.querySelectorAll(".btn-basemap").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    alternarCamadaBase(btn.dataset.base);
                });
            });
            return container;
        }
    });
    new ControleBasemap().addTo(Estado.mapa);

    setTimeout(() => {
        if (Estado.mapa) Estado.mapa.invalidateSize();
    }, 250);

    carregarCamadasMapa();
}

function alternarCamadaBase(tipo) {
    if (!Estado.mapa || Estado.baseAtiva === tipo) return;

    // Remove qualquer camada de fundo ativa
    if (Estado.mapa.hasLayer(Estado.camadasBase.padrao)) {
        Estado.mapa.removeLayer(Estado.camadasBase.padrao);
    }
    if (Estado.mapa.hasLayer(Estado.camadasBase.satelite)) {
        Estado.mapa.removeLayer(Estado.camadasBase.satelite);
    }
    if (Estado.mapa.hasLayer(Estado.camadasBase.rotulos)) {
        Estado.mapa.removeLayer(Estado.camadasBase.rotulos);
    }

    // Adiciona a nova camada solicitada
    try {
        if (tipo === "padrao") {
            Estado.camadasBase.padrao.addTo(Estado.mapa);
            Estado.camadasBase.padrao.bringToBack();
        } else if (tipo === "satelite") {
            Estado.camadasBase.satelite.addTo(Estado.mapa);
            Estado.camadasBase.satelite.bringToBack();
        } else if (tipo === "hibrido") {
            Estado.camadasBase.satelite.addTo(Estado.mapa);
            Estado.camadasBase.rotulos.addTo(Estado.mapa);
            Estado.camadasBase.satelite.bringToBack();
        }
        Estado.baseAtiva = tipo;
    } catch (err) {
        console.warn("Falha ao alternar imagem de satélite, revertendo para mapa convencional:", err);
        Estado.camadasBase.padrao.addTo(Estado.mapa);
        Estado.camadasBase.padrao.bringToBack();
        Estado.baseAtiva = "padrao";
    }

    // Preservação estrita das camadas vetoriais e polígonos na frente
    if (Estado.camadaLimite) {
        Estado.camadaLimite.bringToFront();
    }
    if (Estado.camadaProcessos) {
        Estado.camadaProcessos.bringToFront();
    }

    // Atualiza estado visual do controle
    document.querySelectorAll(".btn-basemap").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.base === Estado.baseAtiva);
    });
}

async function carregarCamadasMapa() {
    const subtitulo = document.getElementById("map-subtitle");
    try {
        if (subtitulo) subtitulo.textContent = "Carregando limite municipal e poligonais...";

        // Camada de limite municipal
        if (!Estado.camadaLimite) {
            const geojsonLimite = await buscarJson("/api/municipio/geojson");
            if (geojsonLimite && geojsonLimite.geometry) {
                Estado.camadaLimite = L.geoJSON(geojsonLimite, {
                    style: {
                        color:       "#2563EB",
                        weight:      2.5,
                        dashArray:   "6, 6",
                        fillColor:   "#2563EB",
                        fillOpacity: 0.03,
                    },
                }).addTo(Estado.mapa);
                Estado.camadaLimite.bringToFront();

                Estado.mapa.fitBounds(Estado.camadaLimite.getBounds(), { padding: [15, 15] });
            }
        }

        // Camada de processos minerários
        const params = new URLSearchParams({ limite: 400 });
        if (Estado.fase)       params.append("fase",      Estado.fase);
        if (Estado.termo)      params.append("termo",     Estado.termo);
        if (Estado.substancia) params.append("substancia",Estado.substancia);
        if (Estado.titular)    params.append("titular",   Estado.titular);
        if (Estado.processo)   params.append("numero",    Estado.processo);

        const geojsonProcessos = await buscarJson(`/api/processos/geojson?${params.toString()}`);

        if (Estado.camadaProcessos) {
            Estado.mapa.removeLayer(Estado.camadaProcessos);
        }
        Estado.poligonosMap.clear();

        if (geojsonProcessos && geojsonProcessos.features) {
            Estado.camadaProcessos = L.geoJSON(geojsonProcessos, {
                style: (feature) => {
                    const fase   = (feature.properties.fase || "").toUpperCase();
                    const eLavra = fase.includes("LAVRA") || fase.includes("LICENCIAMENTO") || fase.includes("EXTRAÇÃO");
                    return {
                        color:       eLavra ? "#059669" : "#D97706",
                        weight:      1.5,
                        fillColor:   eLavra ? "#059669" : "#D97706",
                        fillOpacity: eLavra ? 0.35 : 0.25,
                    };
                },
                onEachFeature: (feature, layer) => {
                    const p = feature.properties;
                    if (p.processo) {
                        Estado.poligonosMap.set(p.processo, layer);
                    }

                    // Hover e clique interativo
                    layer.on({
                        mouseover: (e) => {
                            e.target.setStyle({ weight: 3, fillOpacity: 0.55 });
                        },
                        mouseout: (e) => {
                            if (Estado.camadaProcessos) {
                                Estado.camadaProcessos.resetStyle(e.target);
                            }
                        },
                        click: () => {
                            abrirPainelDetalhe(p);
                        }
                    });

                    // Construção do Popup via DOM seguro (XSS safe)
                    const popupDiv = document.createElement("div");
                    popupDiv.style.cssText = "font-size:12.5px;line-height:1.6;min-width:230px;";

                    const titulo = document.createElement("strong");
                    titulo.style.cssText = "font-size:13.5px;color:#1E293B;display:block;margin-bottom:6px;border-bottom:1px solid #E2E8F0;padding-bottom:4px;";
                    titulo.textContent = `Processo ${p.processo || "—"}`;
                    popupDiv.appendChild(titulo);

                    const linhas = [
                        ["Fase:",            p.fase             || "Não informada"],
                        ["Titular:",         p.nome_titular     || "Não informado"],
                        ["Substância:",      p.substancia       || "Não informada"],
                        ["Área no Mun.:",    `${formatarNumero(p.area_ha_mun)} ha`],
                        ["Área Original:",   `${formatarNumero(p.area_ha_original)} ha`],
                        ["Tipo Recorte:",    p.tipo_recorte     || "INTEGRAL"],
                    ];

                    for (const [rotulo, valor] of linhas) {
                        const item = document.createElement("div");
                        item.style.marginBottom = "3px";
                        const b = document.createElement("b");
                        b.style.color = "#475569";
                        b.textContent = `${rotulo} `;
                        item.appendChild(b);
                        item.appendChild(document.createTextNode(valor));
                        popupDiv.appendChild(item);
                    }

                    layer.bindPopup(popupDiv, { maxWidth: 300 });
                },
            });

            const checkProcessos = document.getElementById("check-camada-processos");
            if (!checkProcessos || checkProcessos.checked) {
                Estado.camadaProcessos.addTo(Estado.mapa);
                Estado.camadaProcessos.bringToFront();
            }

            if (subtitulo) {
                subtitulo.textContent = `${geojsonProcessos.features.length} processos minerários exibidos sobre Parauapebas`;
            }
        }
    } catch {
        if (subtitulo) subtitulo.textContent = "Aviso: Camadas territoriais carregadas com limitações.";
    }
}

function destacarProcessoNoMapa(numeroProcesso) {
    if (!Estado.mapa || !Estado.poligonosMap.has(numeroProcesso)) return;
    const camada = Estado.poligonosMap.get(numeroProcesso);
    Estado.mapa.fitBounds(camada.getBounds(), { padding: [30, 30], maxZoom: 13 });
    camada.openPopup();
}

// ============================================================
//  PAINEL DE DETALHES DO PROCESSO
// ============================================================

function abrirPainelDetalhe(p) {
    const painel = document.getElementById("painel-detalhe-processo");
    if (!painel) return;

    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val || "—";
    };

    set("det-processo",   p.processo);
    set("det-titular",    p.nome_titular);
    set("det-substancia", p.substancia);
    set("det-fase",       p.fase);
    set("det-amparo",     p.autorizado_lavra ? "✔ Fase com amparo de Lavra" : "✘ Sem amparo de extração (Fase preliminar)");
    set("det-evento",     p.ultimo_evento);
    set("det-area-mun",   `${formatarNumero(p.area_ha || p.area_ha_mun)} ha`);
    set("det-area-orig",  `${formatarNumero(p.area_ha_original)} ha`);
    set("det-recorte",    p.tipo_recorte || "INTEGRAL");

    painel.style.display = "block";
}

function fecharPainelDetalhe() {
    const painel = document.getElementById("painel-detalhe-processo");
    if (painel) painel.style.display = "none";

    if (Estado.linhaAtiva) {
        Estado.linhaAtiva.classList.remove("row-selected");
        Estado.linhaAtiva = null;
    }
}

// ============================================================
//  TABELA DE PROCESSOS MINERÁRIOS
// ============================================================

async function carregarTabelaProcessos() {
    const corpo = document.getElementById("tabela-processos-corpo");
    if (!corpo) return;
    corpo.innerHTML = '<tr><td colspan="8" class="table-empty">Consultando base de dados PostGIS...</td></tr>';

    const params = new URLSearchParams({
        limite:             Estado.limite,
        offset:             Estado.pagina * Estado.limite,
        apenas_parauapebas: Estado.apenasParauapebas,
    });

    if (Estado.termo)      params.append("termo",     Estado.termo);
    if (Estado.fase)       params.append("fase",      Estado.fase);
    if (Estado.substancia) params.append("substancia",Estado.substancia);
    if (Estado.titular)    params.append("titular",   Estado.titular);
    if (Estado.processo)   params.append("numero",    Estado.processo);

    try {
        const resposta  = await buscarJson(`/api/processos?${params.toString()}`);
        Estado.total    = resposta.total || 0;

        const counter = document.getElementById("table-counter");
        if (counter) counter.textContent = `${Estado.total.toLocaleString("pt-BR")} registros encontrados`;

        if (!resposta.registros || !resposta.registros.length) {
            corpo.innerHTML = '<tr><td colspan="8" class="table-empty">Nenhum processo minerário encontrado para os filtros informados.</td></tr>';
            atualizarControlesPaginacao();
            return;
        }

        fecharPainelDetalhe();

        corpo.replaceChildren();
        for (const p of resposta.registros) {
            const tr = document.createElement("tr");
            tr.title = "Clique para abrir detalhes e localizar no mapa";

            const tdProcesso = document.createElement("td");
            const strong = document.createElement("strong");
            strong.textContent = p.processo || "—";
            tdProcesso.appendChild(strong);

            const tdFase = document.createElement("td");
            tdFase.textContent = p.fase || "—";

            const tdTitular = document.createElement("td");
            tdTitular.textContent = p.nome_titular || "NÃO INFORMADO";

            const tdSubstancia = document.createElement("td");
            tdSubstancia.textContent = p.substancia || "NÃO INFORMADA";

            const tdAreaMun = document.createElement("td");
            tdAreaMun.textContent = formatarNumero(p.area_ha);

            const tdAreaOrig = document.createElement("td");
            tdAreaOrig.textContent = formatarNumero(p.area_ha_original);

            const tdAmparo = document.createElement("td");
            const spanBadge = document.createElement("span");
            spanBadge.className   = p.autorizado_lavra ? "badge-sim" : "badge-nao";
            spanBadge.textContent = p.autorizado_lavra ? "SIM" : "NÃO";
            tdAmparo.appendChild(spanBadge);

            const tdRecorte = document.createElement("td");
            tdRecorte.textContent = p.tipo_recorte || "INTEGRAL";

            tr.append(tdProcesso, tdFase, tdTitular, tdSubstancia, tdAreaMun, tdAreaOrig, tdAmparo, tdRecorte);

            tr.addEventListener("click", () => {
                if (Estado.linhaAtiva && Estado.linhaAtiva !== tr) {
                    Estado.linhaAtiva.classList.remove("row-selected");
                }
                tr.classList.add("row-selected");
                Estado.linhaAtiva = tr;

                destacarProcessoNoMapa(p.processo);
                abrirPainelDetalhe(p);
            });

            corpo.appendChild(tr);
        }

        atualizarControlesPaginacao();
    } catch {
        corpo.innerHTML = '<tr><td colspan="8" class="table-empty" style="color:#DC2626;">Falha na consulta ao banco de dados PostgreSQL.</td></tr>';
    }
}

// ============================================================
//  PAGINAÇÃO DA TABELA
// ============================================================

function atualizarControlesPaginacao() {
    const info      = document.getElementById("pagination-info");
    const indicador = document.getElementById("pag-indicador");
    const btnAnt    = document.getElementById("btn-pag-anterior");
    const btnProx   = document.getElementById("btn-pag-proximo");

    const totalPaginas = Math.ceil(Estado.total / Estado.limite) || 1;
    const paginaAtual  = Estado.pagina + 1;

    const inicio = Estado.total === 0 ? 0 : Estado.pagina * Estado.limite + 1;
    const fim    = Math.min((Estado.pagina + 1) * Estado.limite, Estado.total);

    if (info)      info.textContent      = `Mostrando ${inicio} a ${fim} de ${Estado.total.toLocaleString("pt-BR")} processos`;
    if (indicador) indicador.textContent = `Página ${paginaAtual} de ${totalPaginas}`;

    if (btnAnt)  btnAnt.disabled  = Estado.pagina === 0;
    if (btnProx) btnProx.disabled = fim >= Estado.total;
}

// ============================================================
//  VINCULAÇÃO DE EVENTOS
// ============================================================

function configurarEventos() {
    let timerBusca;

    const capturarFiltros = () => {
        Estado.termo              = (document.getElementById("campo-termo")?.value     || "").trim();
        Estado.titular            = (document.getElementById("campo-titular")?.value   || "").trim();
        Estado.substancia         = (document.getElementById("campo-substancia")?.value|| "").trim();
        Estado.processo           = (document.getElementById("campo-processo")?.value  || "").trim();
        Estado.fase               = document.getElementById("campo-fase")?.value       || "";
        Estado.apenasParauapebas  = true;
        Estado.pagina             = 0;
    };

    const dispararBuscaComDebounce = () => {
        clearTimeout(timerBusca);
        timerBusca = setTimeout(() => {
            capturarFiltros();
            carregarTabelaProcessos();
            carregarCamadasMapa();
        }, 350);
    };

    ["campo-termo", "campo-titular", "campo-substancia", "campo-processo"].forEach(id => {
        document.getElementById(id)?.addEventListener("input", dispararBuscaComDebounce);
    });

    ["campo-fase"].forEach(id => {
        document.getElementById(id)?.addEventListener("change", dispararBuscaComDebounce);
    });

    document.getElementById("btn-executar-busca")?.addEventListener("click", () => {
        clearTimeout(timerBusca);
        capturarFiltros();
        carregarTabelaProcessos();
        carregarCamadasMapa();
    });

    const btnToggle     = document.getElementById("btn-toggle-filtros");
    const painelFiltros = document.getElementById("painel-filtros-avancados");
    if (btnToggle && painelFiltros) {
        btnToggle.addEventListener("click", () => {
            const visivel = painelFiltros.style.display !== "none";
            painelFiltros.style.display = visivel ? "none" : "block";
            btnToggle.textContent = visivel ? "Filtros Avançados ▼" : "Recolher Filtros ▲";
        });
    }

    document.getElementById("btn-limpar-filtros")?.addEventListener("click", () => {
        ["campo-termo", "campo-titular", "campo-substancia", "campo-processo"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = "";
        });
        const fase = document.getElementById("campo-fase");
        if (fase) fase.value = "";

        Estado.termo = Estado.titular = Estado.substancia = Estado.processo = Estado.fase = "";
        Estado.apenasParauapebas = true;
        Estado.pagina = 0;

        carregarTabelaProcessos();
        carregarCamadasMapa();
    });

    document.getElementById("btn-pag-anterior")?.addEventListener("click", () => {
        if (Estado.pagina > 0) {
            Estado.pagina--;
            carregarTabelaProcessos();
        }
    });

    document.getElementById("btn-pag-proximo")?.addEventListener("click", () => {
        if ((Estado.pagina + 1) * Estado.limite < Estado.total) {
            Estado.pagina++;
            carregarTabelaProcessos();
        }
    });

    document.getElementById("btn-ajustar-zoom")?.addEventListener("click", () => {
        if (Estado.camadaLimite && Estado.mapa) {
            Estado.mapa.fitBounds(Estado.camadaLimite.getBounds(), { padding: [15, 15] });
        }
    });

    document.getElementById("check-camada-limite")?.addEventListener("change", (e) => {
        if (!Estado.camadaLimite || !Estado.mapa) return;
        if (e.target.checked) Estado.mapa.addLayer(Estado.camadaLimite);
        else Estado.mapa.removeLayer(Estado.camadaLimite);
    });

    document.getElementById("check-camada-processos")?.addEventListener("change", (e) => {
        if (!Estado.camadaProcessos || !Estado.mapa) return;
        if (e.target.checked) Estado.mapa.addLayer(Estado.camadaProcessos);
        else Estado.mapa.removeLayer(Estado.camadaProcessos);
    });

    document.getElementById("btn-fechar-detalhe")?.addEventListener("click", fecharPainelDetalhe);
}

// ============================================================
//  INICIALIZAÇÃO DO SISTEMA
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    configurarEventos();
    try {
        inicializarMapa();
    } catch (erro) {
        console.error("Falha ao inicializar o mapa Leaflet:", erro);
    }
    atualizarStatusBanco();
    atualizarIndicadores();
    carregarFiltroFases();
    carregarTabelaProcessos();
});
