(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const keys = ['mes', 'bimestre', 'semestre', 'ano'];
  const number = new Intl.NumberFormat('pt-BR');
  const date = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' });
  let data;
  let selected = keys.includes(new URLSearchParams(location.search).get('period')) ? new URLSearchParams(location.search).get('period') : 'mes';

  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function formatDate(value) {
    if (!value) return 'data não informada';
    const parsed = new Date(value.length === 10 ? `${value}T12:00:00Z` : value);
    return Number.isNaN(parsed.getTime()) ? 'data não informada' : date.format(parsed);
  }
  function safeLink(value, fallback = 'https://github.com/LordCarvel') {
    try { const url = new URL(value); return url.protocol === 'https:' ? url.href : fallback; } catch { return fallback; }
  }
  function hours(value) {
    const minutes = Math.floor(Math.max(0, Number(value) || 0) / 60);
    return `${number.format(Math.floor(minutes / 60))}h ${String(minutes % 60).padStart(2, '0')}min`;
  }
  function svgNode(tag, attrs, text) {
    const item = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([key, value]) => item.setAttribute(key, String(value)));
    if (text !== undefined) item.textContent = text;
    return item;
  }
  function aggregate(days) {
    if (days.length <= 62) return days.map(day => ({ label: day.date.slice(8) + '/' + day.date.slice(5, 7), count: day.count, date: day.date }));
    const grouped = new Map();
    days.forEach(day => {
      const month = day.date.slice(0, 7);
      grouped.set(month, (grouped.get(month) || 0) + day.count);
    });
    return [...grouped].map(([month, count]) => ({ label: month.slice(5) + '/' + month.slice(2, 4), count, date: month }));
  }
  function renderChart(period) {
    const target = $('chart'); target.replaceChildren();
    const days = (period.days || []).map(day => ({ date: day.date, count: Math.max(0, Number(day.count) || 0) })).sort((a, b) => a.date.localeCompare(b.date));
    const rows = aggregate(days);
    $('chart-unit').textContent = days.length <= 62 ? 'por dia' : 'por mês';
    if (!rows.length || !rows.some(row => row.count > 0)) {
      target.append(node('p', 'Ainda não há contribuições registradas neste período.', 'empty'));
      $('chart-summary').textContent = 'O gráfico aparece quando houver atividade pública neste intervalo.';
      return;
    }
    const width = 650, height = 215, left = 4, bottom = 182, available = 642;
    const maximum = Math.max(1, ...rows.map(row => row.count));
    const cell = available / rows.length;
    const chart = svgNode('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-labelledby': 'chart-title chart-desc' });
    chart.append(svgNode('title', { id: 'chart-title' }, `Contribuições — ${period.label}`));
    chart.append(svgNode('desc', { id: 'chart-desc' }, rows.map(row => `${row.label}: ${row.count}`).join('; ')));
    chart.append(svgNode('line', { x1: 0, y1: bottom, x2: width, y2: bottom, class: 'baseline' }));
    rows.forEach((row, index) => {
      const x = left + index * cell, barHeight = row.count / maximum * 145;
      const bar = svgNode('rect', { x, y: bottom - barHeight, width: Math.max(2, cell * .64), height: Math.max(row.count ? 2 : 0, barHeight), rx: 2, class: 'bar' });
      bar.append(svgNode('title', {}, `${row.label}: ${number.format(row.count)} contribuições`));
      chart.append(bar);
      const step = Math.ceil(rows.length / 9);
      if (index % step === 0 || index === rows.length - 1) chart.append(svgNode('text', { x: x + cell * .32, y: 204, 'text-anchor': 'middle' }, row.label));
    });
    target.append(chart);
    const top = rows.reduce((best, row) => row.count > best.count ? row : best, rows[0]);
    $('chart-summary').textContent = `Maior volume ${days.length <= 62 ? 'no dia' : 'no mês'} ${top.label}: ${number.format(top.count)} contribuições.`;
  }
  function renderCalendar(period) {
    const target = $('calendar'); target.replaceChildren();
    const days = [...(period.days || [])].sort((a, b) => a.date.localeCompare(b.date));
    if (!days.length) { target.append(node('p', 'Sem dados de calendário neste período.', 'empty')); return; }
    const start = new Date(days[0].date + 'T12:00:00Z').getUTCDay();
    for (let i = 0; i < start; i++) target.append(node('span', '', 'day empty-day'));
    days.forEach(day => {
      const count = Math.max(0, Number(day.count) || 0);
      const item = node('span', '', 'day');
      item.dataset.level = count === 0 ? '0' : String(Math.min(4, 1 + Math.floor((count - 1) / 3)));
      item.title = `${formatDate(day.date)}: ${number.format(count)} contribuições`;
      item.setAttribute('aria-label', item.title);
      target.append(item);
    });
  }
  function renderRepos(period) {
    const list = $('active-repos'); list.replaceChildren();
    const repos = [...(period.repositories || [])].filter(repo => repo.commits > 0).sort((a, b) => b.commits - a.commits);
    if (!repos.length) { list.append(node('li', 'Nenhum commit público neste período.', 'empty')); return; }
    repos.slice(0, 8).forEach(repo => {
      const item = node('li');
      const link = node('a', repo.name); link.href = safeLink(repo.url);
      const total = node('strong', number.format(repo.commits)); total.setAttribute('aria-label', `${repo.commits} commits`);
      item.append(link, total); list.append(item);
    });
  }
  function renderPeriod(key, updateURL = true) {
    if (!data || !data.periods[key]) return;
    selected = key;
    const period = data.periods[key];
    document.querySelectorAll('[data-period]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.period === key)));
    $('period-range').textContent = `${period.label} · ${formatDate(period.start)} a ${formatDate(period.end)}`;
    $('metric-contributions').textContent = number.format(period.contributions || 0);
    $('metric-commits').textContent = number.format(period.commits || 0);
    $('metric-days').textContent = number.format(period.active_days || 0);
    renderChart(period); renderCalendar(period); renderRepos(period);
    if (updateURL) { const url = new URL(location.href); url.searchParams.set('period', key); history.replaceState(null, '', url); }
  }
  function renderProjects(projects) {
    const target = $('projects-list'); target.replaceChildren();
    if (!projects.length) { target.append(node('p', 'Os projetos estão disponíveis no GitHub.', 'empty')); return; }
    projects.forEach(project => {
      const article = node('article', undefined, 'project');
      const copy = node('div', undefined, 'project-copy');
      copy.append(node('p', `~/projetos/${project.name}`, 'project-path'));
      const title = node('h3'), link = node('a', project.title || project.name); link.href = safeLink(project.url); title.append(link); copy.append(title);
      copy.append(node('p', project.summary));
      const extra = node('div', undefined, 'project-extra');
      const tags = node('ul', undefined, 'tags'); tags.setAttribute('aria-label', 'Tecnologias');
      (project.stack || []).forEach(tech => tags.append(node('li', tech)));
      extra.append(tags);
      extra.append(node('p', `${number.format(project.commits || 0)} commits no repositório · último push em ${formatDate(project.pushed_at)}`, 'project-meta'));
      article.append(copy, extra); target.append(article);
    });
  }
  function renderWaka(waka) {
    const target = $('waka-content'); target.replaceChildren();
    if (!waka || typeof waka.total_seconds !== 'number') {
      target.append(node('p', 'O tempo de programação não está público no WakaTime. Os projetos e a atividade do GitHub continuam disponíveis.', 'empty')); return;
    }
    const total = node('div', undefined, 'waka-total');
    total.append(node('strong', hours(waka.total_seconds)), node('p', 'de programação registrada'));
    const range = waka.range === 'all_time' ? 'Histórico completo disponível no WakaTime.' : 'Período público selecionado no WakaTime.';
    total.append(node('p', range, 'range-label'));
    const list = node('ul', undefined, 'language-list'); list.setAttribute('aria-label', 'Tempo por linguagem no WakaTime');
    (waka.languages || []).slice(0, 6).forEach(language => {
      const item = node('li'), head = node('div', undefined, 'language-head');
      const percent = Math.max(0, Math.min(100, Number(language.percent) || 0));
      head.append(node('span', language.name), node('span', `${percent.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`));
      const track = node('div', undefined, 'track'), bar = node('span'); bar.style.width = `${percent}%`; track.append(bar); track.setAttribute('aria-hidden', 'true');
      item.append(head, track); list.append(item);
    });
    target.append(total, list);
  }
  async function load() {
    const status = $('load-status'); status.hidden = false; status.classList.remove('error'); status.textContent = 'Buscando os dados públicos…';
    try {
      const response = await fetch('./data.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error('Dados indisponíveis');
      data = await response.json();
      if (!data.periods || !keys.every(key => data.periods[key])) throw new Error('Períodos incompletos');
      renderProjects(data.profile?.projects || []); renderWaka(data.wakatime);
      $('updated').textContent = `Atualizado em ${formatDate(data.updated_at)}`;
      renderPeriod(selected, false);
      $('activity-content').hidden = false; status.hidden = true;
    } catch {
      status.classList.add('error'); status.textContent = 'Não foi possível carregar os dados agora.';
      const retry = node('button', 'Tentar novamente', 'retry'); retry.type = 'button'; retry.addEventListener('click', load); status.append(retry);
      $('projects-list').replaceChildren(node('p', 'Você pode conhecer os projetos diretamente no GitHub pelos links desta página.', 'empty'));
      $('waka-content').replaceChildren(node('p', 'O histórico também pode ser consultado no perfil do WakaTime.', 'empty'));
    }
  }
  document.querySelectorAll('[data-period]').forEach(button => button.addEventListener('click', () => renderPeriod(button.dataset.period)));
  window.addEventListener('popstate', () => { const key = new URLSearchParams(location.search).get('period'); renderPeriod(keys.includes(key) ? key : 'mes', false); });
  load();
})();
