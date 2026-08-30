/* ===========================================================================
   EXTRATOR DE ELENCOS — rode no console do navegador
   ===========================================================================

   COMO USAR
   1. Abra a pagina de elencos da liga, ja logado
   2. Pressione F12 e va na aba "Console"
   3. Cole este arquivo inteiro e pressione Enter
   4. Rode:   extrair('Liga 5')
   5. O CSV e copiado para a area de transferencia e tambem exibido no console

   POR QUE ISSO E MELHOR QUE COPIAR E COLAR
   A exportacao por texto perde as posicoes: elas sao imagens, e imagem nao
   copia como texto (viram "img1", "img1img2"). Lendo o DOM da pagina, da para
   recuperar PG/SG/SF/PF/C de verdade, a partir do alt, do title ou do nome do
   arquivo da imagem.

   ATENCAO
   Este script foi escrito SEM acesso ao site (esta atras de login), entao ele
   e deliberadamente generico e defensivo: procura tabelas, tenta varias
   estrategias e RELATA o que encontrou. Se a saida vier torta, rode
   diagnosticar() e me mande o resultado que eu ajusto para o HTML real.
   =========================================================================== */

(function () {
  'use strict';

  const POSICOES_VALIDAS = ['PG', 'SG', 'SF', 'PF', 'C'];

  // Acumulador entre execucoes. Serve para dois casos:
  //   - o site mostra uma franquia por vez (roda em cada pagina)
  //   - voce quer juntar varias ligas num CSV so
  //
  // Guardado em localStorage, e nao em variavel: ao navegar para outra pagina
  // o objeto `window` e recriado do zero e uma variavel comum seria perdida.
  // ATENCAO: localStorage e por SITE. Se as ligas estiverem em dominios
  // diferentes, o acervo nao atravessa; baixe um CSV por site e junte depois.
  const CHAVE_ACERVO = '__acervo_elencos';

  function lerAcervo() {
    try { return JSON.parse(localStorage.getItem(CHAVE_ACERVO) || '[]'); }
    catch (e) { return []; }
  }

  function gravarAcervo(lista) {
    try { localStorage.setItem(CHAVE_ACERVO, JSON.stringify(lista)); }
    catch (e) { console.warn('Nao foi possivel gravar o acervo:', e.message); }
  }

  // -------------------------------------------------------------------------
  // Utilidades
  // -------------------------------------------------------------------------
  function limpar(txt) {
    return (txt || '')
      // Marcadores visuais que a plataforma anexa ao nome (calouro, designado)
      // e espaco fixo. Inclui \u00c2, que aparece como residuo "Â" quando a
      // pagina serve UTF-8 mas o navegador interpretou como latin-1.
      .replace(/[\u00ae\u00d0\u00a0\u00c2\u00ad]/g, ' ')
      .replace(/\s+/g, ' ')
      // remove pontuacao solta que sobra no fim apos limpar os marcadores
      .replace(/[\s\-–—•|]+$/, '')
      .trim();
  }

  function paraNumero(txt) {
    const t = limpar(txt).replace(/\$/g, '').trim();
    if (!t || t === '-' || t === '--') return '';
    const digitos = t.replace(/[.\s]/g, '').replace(',', '.');
    if (!/^-?\d+(\.\d+)?$/.test(digitos)) return '';
    return String(Math.round(parseFloat(digitos)));
  }

  // Tenta descobrir a posicao a partir de uma imagem.
  // Cobre alt, title, aria-label e o nome do arquivo no src.
  function posicaoDeImagem(img) {
    const candidatos = [img.alt, img.title, img.getAttribute('aria-label'), img.src];
    for (const c of candidatos) {
      if (!c) continue;
      const texto = c.toUpperCase();
      // procura token isolado (evita casar "C" dentro de "SOCCER")
      for (const p of ['PG', 'SG', 'SF', 'PF']) {
        if (new RegExp('(^|[^A-Z])' + p + '([^A-Z]|$)').test(texto)) return p;
      }
      if (/(^|[^A-Z])C([^A-Z]|$)/.test(texto)) return 'C';
    }
    return null;
  }

  function posicoesDaCelula(celula) {
    const achadas = [];

    // 1) imagens
    celula.querySelectorAll('img').forEach(img => {
      const p = posicaoDeImagem(img);
      if (p && !achadas.includes(p)) achadas.push(p);
    });

    // 2) texto puro (ex.: "PG SG" ou "PG/SG")
    if (!achadas.length) {
      const txt = limpar(celula.textContent).toUpperCase();
      txt.split(/[^A-Z]+/).forEach(tok => {
        if (POSICOES_VALIDAS.includes(tok) && !achadas.includes(tok)) achadas.push(tok);
      });
    }

    // 3) classes CSS (ex.: class="badge pos-pg")
    if (!achadas.length) {
      celula.querySelectorAll('[class]').forEach(el => {
        const cls = el.className.toString().toUpperCase();
        POSICOES_VALIDAS.forEach(p => {
          if (new RegExp('(^|[^A-Z])' + p + '([^A-Z]|$)').test(cls) && !achadas.includes(p)) {
            achadas.push(p);
          }
        });
      });
    }

    return achadas.join('/');
  }

  // Sobe no DOM procurando o nome da franquia acima da tabela.
  function franquiaDaTabela(tabela) {
    let no = tabela;
    for (let nivel = 0; nivel < 6 && no; nivel++) {
      let irmao = no.previousElementSibling;
      while (irmao) {
        // titulos sao os candidatos mais provaveis
        const titulo = irmao.querySelector
          ? irmao.querySelector('h1,h2,h3,h4,h5,.titulo,.team-name,.franchise')
          : null;
        if (titulo && limpar(titulo.textContent)) return limpar(titulo.textContent);
        const t = limpar(irmao.textContent);
        if (t && t.length < 60 && !/\$|\d{4}-\d{4}/.test(t)) return t;
        irmao = irmao.previousElementSibling;
      }
      no = no.parentElement;
    }
    return '';
  }

  // Le os anos do cabecalho (2025-2026, 2026-27, 2025 etc.)
  function anosDoCabecalho(tabela) {
    const anos = [];
    const linha = tabela.querySelector('thead tr') || tabela.querySelector('tr');
    if (!linha) return anos;
    linha.querySelectorAll('th,td').forEach((c, i) => {
      const m = limpar(c.textContent).match(/(\d{4})\s*[-/]?\s*\d{0,4}/);
      if (m && +m[1] >= 2020 && +m[1] <= 2040) anos.push({ indice: i, ano: +m[1] });
    });
    return anos;
  }

  // -------------------------------------------------------------------------
  // Diagnostico: use quando a extracao vier estranha
  // -------------------------------------------------------------------------
  window.diagnosticar = function () {
    const tabelas = [...document.querySelectorAll('table')];
    console.log(`Tabelas encontradas: ${tabelas.length}`);
    tabelas.slice(0, 5).forEach((t, i) => {
      const linhas = t.querySelectorAll('tr');
      const cab = [...(linhas[0] ? linhas[0].querySelectorAll('th,td') : [])]
        .map(c => limpar(c.textContent)).join(' | ');
      console.log(`\n--- tabela ${i} --- ${linhas.length} linhas`);
      console.log('  cabecalho :', cab.slice(0, 160));
      console.log('  franquia  :', franquiaDaTabela(t));
      console.log('  anos      :', JSON.stringify(anosDoCabecalho(t)));
      if (linhas[1]) {
        console.log('  1a linha  :',
          [...linhas[1].querySelectorAll('td')].map(c => limpar(c.textContent)).join(' | ').slice(0, 160));
        console.log('  imgs      :', linhas[1].querySelectorAll('img').length);
        const img = linhas[1].querySelector('img');
        if (img) console.log('  img src   :', img.src, '| alt:', img.alt, '| title:', img.title);
      }
    });
    console.log('\nSe nao houver <table>, o site usa divs. Me mande o resultado de:');
    console.log("  copy(document.querySelector('SELETOR_DA_LISTA').outerHTML)");
  };

  // -------------------------------------------------------------------------
  // Extracao principal
  // -------------------------------------------------------------------------
  window.extrair = function (nomeLiga, opcoes) {
    opcoes = opcoes || {};
    if (!nomeLiga) {
      console.error('Informe a liga. Exemplo:  extrair("Liga 5")');
      return;
    }

    const tabelas = [...document.querySelectorAll('table')]
      .filter(t => t.querySelectorAll('tr').length >= 2);

    if (!tabelas.length) {
      console.error('Nenhuma tabela encontrada. Rode diagnosticar() para investigar.');
      return;
    }

    const registros = [];
    const anosVistos = new Set();
    let semFranquia = 0;

    tabelas.forEach(tabela => {
      const franquia = opcoes.franquia || franquiaDaTabela(tabela);
      if (!franquia) semFranquia++;

      const anos = anosDoCabecalho(tabela);
      anos.forEach(a => anosVistos.add(a.ano));

      const linhas = [...tabela.querySelectorAll('tbody tr')];
      const alvo = linhas.length ? linhas : [...tabela.querySelectorAll('tr')].slice(1);

      alvo.forEach(tr => {
        const celulas = [...tr.querySelectorAll('td')];
        if (celulas.length < 2) return;

        // O nome e a primeira celula com texto que nao seja numero nem dinheiro
        let nome = '';
        let idxNome = -1;
        for (let i = 0; i < celulas.length; i++) {
          const t = limpar(celulas[i].textContent);
          if (t && !/^[\d.,\s$-]+$/.test(t)) { nome = t; idxNome = i; break; }
        }
        if (!nome) return;

        // Posicao: procura na celula seguinte ao nome, depois em qualquer celula
        let posicao = '';
        for (let i = idxNome; i < Math.min(idxNome + 3, celulas.length); i++) {
          posicao = posicoesDaCelula(celulas[i]);
          if (posicao) break;
        }

        const reg = { jogador: nome, liga: nomeLiga, equipe_fantasy: franquia, posicao, salarios: {} };
        anos.forEach(a => {
          if (celulas[a.indice]) {
            const v = paraNumero(celulas[a.indice].textContent);
            if (v !== '') reg.salarios[a.ano] = v;
          }
        });
        registros.push(reg);
      });
    });

    if (!registros.length) {
      console.error('Nenhum jogador extraido. Rode diagnosticar().');
      return;
    }

    // Registra no acervo, permitindo juntar varias paginas/ligas.
    // Evita duplicar se voce rodar duas vezes na mesma pagina.
    if (opcoes.acumular !== false) {
      const acervo = lerAcervo();
      const jaTem = new Set(acervo.map(r => `${r.liga}|${r.equipe_fantasy}|${r.jogador}`));
      let novos = 0;
      registros.forEach(r => {
        const ch = `${r.liga}|${r.equipe_fantasy}|${r.jogador}`;
        if (!jaTem.has(ch)) { acervo.push(r); jaTem.add(ch); novos++; }
      });
      gravarAcervo(acervo);
      if (novos < registros.length) {
        console.log(`  (${registros.length - novos} ja estavam no acervo, ignorados)`);
      }
    }

    const anos = [...anosVistos].sort();
    const campos = ['jogador', 'liga', 'equipe_fantasy', 'posicao']
      .concat(anos.map(a => 'sal_' + a))
      .concat(['draft_pick', 'idade', 'lesao', 'ano_retorno']);

    const escapar = v => {
      const s = String(v == null ? '' : v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };

    const linhasCsv = [campos.join(',')];
    registros.forEach(r => {
      const linha = [r.jogador, r.liga, r.equipe_fantasy, r.posicao]
        .concat(anos.map(a => r.salarios[a] || ''))
        .concat(['', '', '', '']);
      linhasCsv.push(linha.map(escapar).join(','));
    });
    const csv = linhasCsv.join('\n');

    const franquias = new Set(registros.map(r => r.equipe_fantasy));
    const comPos = registros.filter(r => r.posicao).length;
    const comSal = registros.filter(r => Object.keys(r.salarios).length).length;

    console.log('===== EXTRACAO CONCLUIDA =====');
    console.log(`  liga        : ${nomeLiga}`);
    console.log(`  franquias   : ${franquias.size}`);
    console.log(`  jogadores   : ${registros.length}`);
    console.log(`  com posicao : ${comPos}  ${comPos < registros.length * 0.8 ? '<-- baixo, rode diagnosticar()' : ''}`);
    console.log(`  com salario : ${comSal}`);
    console.log(`  anos        : ${anos.join(', ')}`);
    if (semFranquia) console.log(`  AVISO: ${semFranquia} tabela(s) sem franquia identificada`);
    console.log('\nCSV copiado para a area de transferencia.');

    try {
      copy(csv);              // funcao do console do navegador
    } catch (e) {
      console.log('Copie manualmente abaixo:');
    }
    console.log(csv.slice(0, 1500) + (csv.length > 1500 ? '\n... (truncado na exibicao)' : ''));

    window.ultimoCSV = csv;
    console.log(`\n  Acervo acumulado: ${lerAcervo().length} jogadores.`);
    console.log('  Quando terminar todas as ligas, rode:  baixarTudo()');
    return csv;
  };

  // -------------------------------------------------------------------------
  // Monta o CSV de TUDO que foi acumulado e baixa como arquivo.
  // Baixar e mais confiavel que a area de transferencia quando sao varias
  // ligas: nao depende de colar no lugar certo nem corre risco de sobrescrever.
  // -------------------------------------------------------------------------
  window.baixarTudo = function (nomeArquivo) {
    const acervo = lerAcervo();
    if (!acervo.length) {
      console.error('Acervo vazio. Rode extrair("Liga X") pelo menos uma vez.');
      return;
    }

    const anos = [...new Set(acervo.flatMap(r => Object.keys(r.salarios).map(Number)))].sort();
    const campos = ['jogador', 'liga', 'equipe_fantasy', 'posicao']
      .concat(anos.map(a => 'sal_' + a))
      .concat(['draft_pick', 'idade', 'lesao', 'ano_retorno']);

    const escapar = v => {
      const s = String(v == null ? '' : v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };

    const linhas = [campos.join(',')];
    acervo.forEach(r => {
      linhas.push([r.jogador, r.liga, r.equipe_fantasy, r.posicao]
        .concat(anos.map(a => r.salarios[a] || ''))
        .concat(['', '', '', ''])
        .map(escapar).join(','));
    });

    const csv = linhas.join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nomeArquivo || 'elencos_brutos.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    const porLiga = {};
    acervo.forEach(r => { porLiga[r.liga] = (porLiga[r.liga] || 0) + 1; });
    console.log('===== ARQUIVO BAIXADO =====');
    console.log(`  ${acervo.length} jogadores | anos ${anos[0]} a ${anos[anos.length - 1]}`);
    Object.entries(porLiga).forEach(([l, n]) => console.log(`  ${l}: ${n}`));
    console.log('\n  Mova o arquivo para a pasta do projeto e rode:');
    console.log('    python importar_csv.py');
    console.log('    python gerar_dados.py');
  };

  // Limpa o acervo, caso queira recomecar do zero
  window.limparAcervo = function () {
    gravarAcervo([]);
    console.log('Acervo limpo.');
  };

  console.log('Extrator carregado.');
  console.log('  extrair("Liga 5")   -> extrai a pagina atual e acumula');
  console.log('  baixarTudo()        -> baixa o CSV com tudo que foi acumulado');
  console.log('  limparAcervo()      -> recomeca do zero');
  console.log('  diagnosticar()      -> mostra o que ha na pagina, se algo falhar');
})();
