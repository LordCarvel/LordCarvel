"""Render a cohesive Neovim-inspired profile from current public data."""

from collections import Counter
import datetime as dt
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, GREEN, GOLD = "#e7e6df", "#9caa99", "#a7d88b", "#e6bc80"
COLORS = [GREEN, GOLD, "#8fc5d4", "#baa4d9", "#d99788", "#91a6ce"]
PROJECTS = [
    ("Cdatra", "Persistência em Java", "Uma classe anotada. Menos JDBC repetitivo.",
     ["Entidades, reflexão e Repository<T> para operações de CRUD.",
      "Filtros de consulta, validação de metadados e transações.",
      "Testes com JUnit e H2; cobertura com JaCoCo."], "Java 17 / JDBC / SQL / Maven / JUnit"),
    ("EasyPrintV2", "Easy Hub", "Pedidos, comandas e uma operação mais organizada.",
     ["Configuração de modelos e impressão de comandas térmicas.",
      "Interface React e servidor Node.js para compartilhar pedidos.",
      "Aplicação desktop em Electron, distribuída para Windows."], "React / Node.js / SQLite / Electron"),
    ("Delivery-Board-V2", "Delivery Board", "Organização de entregadores e pedidos por rodada.",
     ["Fluxos de entrega, edição de pedidos e dados no navegador."], "JavaScript / React / Vite / localStorage"),
    ("Finally-Storage", "Finally Storage", "Conferência de valores e fechamento diário de caixa.",
     ["Totais de entregadores e separação por forma de pagamento."], "JavaScript / HTML / CSS / localStorage"),
]


def txt(x, y, value, size=24, color=INK, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill, radius=0, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" {extra}/>'


def panel(name, height, tab, body, description, footer="", accent=GREEN):
    output = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(tab)}</title><desc id="desc">{escape(description)}</desc>
<style>
text{{font-family:'Cascadia Code','DejaVu Sans Mono',Consolas,monospace}}
.cursor{{animation:blink 1.25s steps(1) infinite}}
@keyframes blink{{0%,55%{{opacity:1}}56%,100%{{opacity:0}}}}
@media(prefers-reduced-motion:reduce){{.cursor{{animation:none}}}}
</style>
{rect(1,1,958,height-2,"#101610",12,'stroke="#354333"')}
{rect(2,2,956,49,"#1b251b",11)}
{rect(2,38,956,13,"#1b251b")}
{rect(2,2,5,49,accent)}
{txt(29,34,'▸ '+tab,20,accent)}
{txt(930,34,'carvel / workspace',16,MUTED,'text-anchor="end"')}
{body}
{rect(2,height-39,956,37,"#1b251b")}
{rect(2,height-39,126,37,accent)}
{txt(64,height-14,'NORMAL',16,'#101610','text-anchor="middle" font-weight="700"')}
{txt(149,height-14,footer or tab,16,MUTED)}
{txt(931,height-14,'utf-8',16,MUTED,'text-anchor="end"')}
</svg>'''
    (ROOT / "assets" / name).write_text(output+"\n", encoding="utf-8")


def duration(seconds):
    minutes = int(seconds or 0) // 60
    return f"{minutes//60}h {minutes%60:02d}min"


def monthly_counts(weeks):
    result = Counter()
    for week in weeks:
        for day in week["contributionDays"]:
            result[day["date"][:7]] += day["contributionCount"]
    return sorted(result.items())[-12:]


def distribution(nodes):
    counts = Counter()
    for node in nodes:
        if not node["isFork"]:
            for edge in node["languages"]["edges"]:
                counts[edge["node"]["name"]] += edge["size"]
    total = sum(counts.values())
    ranked = counts.most_common(5)
    other = total-sum(n for _, n in ranked)
    if other:
        ranked.append(("Outras", other))
    return [(name, n/total*100) for name, n in ranked] if total else []


def render_header(user, waka, stamp):
    collection = user["contributionsCollection"]
    count = collection["contributionCalendar"]["totalContributions"]
    body = txt(36,94,"~ $ nvim perfil.md",22,GREEN)
    body += txt(33,160,"1",18,MUTED) + txt(78,170,"CARVEL",78,INK,'font-weight="700" letter-spacing="-3"')
    body += rect(330,109,40,68,GREEN,0,'class="cursor"')
    body += txt(33,211,"2",18,MUTED) + txt(78,214,"Desenvolvimento backend",31,GOLD)
    body += txt(33,255,"3",18,MUTED) + txt(78,257,"Java, dados e aplicações para o dia a dia.",22,MUTED)
    body += rect(32,283,896,1,"#354333")
    body += txt(36,321,f'{user["repositories"]["totalCount"]} repositórios públicos',21,GREEN)
    body += txt(36,353,f'{count} contribuições / 12 meses',21,MUTED)
    if waka:
        body += txt(520,321,duration(waka.get("total_seconds"))+" registrados",21,GOLD)
        body += txt(520,353,"WakaTime / "+("histórico completo" if waka.get("range")=="all_time" else "período público"),19,MUTED)
    panel("termux.svg",418,"perfil.md",body,"Carvel, desenvolvimento backend com Java. "+f"{count} contribuições em 12 meses.",f"dados públicos / {stamp}")


def render_about():
    lines = [
        ("# Sou o Carvel. Meu foco é backend com Java.",GREEN),
        ("Gosto de construir ferramentas que resolvem",INK),
        ("problemas que eu conheço de perto.",INK),
        ("",INK),
        ("Pedidos, impressão, entregas e caixa: foi com essas",INK),
        ("rotinas que vários dos meus projetos ganharam forma.",INK),
        ("",INK),
        ("No Cdatra, aprofundo Java, persistência e testes.",INK),
        ("Nos apps, conecto interface, dados e uso no dia a dia.",INK),
    ]
    body = ""
    for i,(line,color) in enumerate(lines):
        y = 99+i*35
        body += txt(46,y,str(i+1),17,MUTED,'text-anchor="end"')+txt(76,y,line,24,color)
    panel("about.svg",453,"sobre.md",body," ".join(line for line,_ in lines),"Java / backend / persistência")


def render_stack():
    sections = [
        (32,99,"[backend]",[("linguagens",'"Java 17, Node.js"'),("dados",'"JDBC, SQL, H2, SQLite"'),("fundamentos",'"OOP, generics, reflexão"')]),
        (510,99,"[web.desktop]",[("interface",'"React, JavaScript"'),("plataforma",'"Electron, Vite"'),("base",'"HTML, CSS"')]),
        (32,285,"[qualidade]",[("testes",'"JUnit, H2"'),("build",'"Maven, JaCoCo"')]),
        (510,285,"[ferramentas]",[("versão",'"Git, GitHub"'),("rotina",'"Actions, Neovim"')]),
    ]
    body = ""
    for x,y,title,rows in sections:
        body += txt(x,y,title,24,GREEN)
        for i,(key,value) in enumerate(rows):
            body += txt(x,y+37+i*39,key,19,MUTED)
            body += txt(x+155,y+37+i*39,value,18,GOLD)
    panel("stack.svg",444,"stack.toml",body,"Java, Node.js, JDBC, SQL, H2, SQLite, React, Electron, JUnit, Maven, JaCoCo, Git e Neovim.","tecnologias usadas nos projetos")


def render_projects(nodes):
    by_name = {node["name"]:node for node in nodes}
    for slug,title,summary,lines,stack in PROJECTS:
        repo = by_name.get(slug)
        if not repo:
            continue
        body = txt(32,104,title,34,INK,'font-weight="700"')
        body += txt(32,146,summary,23,GOLD)
        for i,line in enumerate(lines):
            body += txt(32,191+i*34,"│ "+line,22,MUTED)
        y = 191+len(lines)*34
        body += txt(32,y+10,stack,20,GREEN)
        branch = repo.get("defaultBranchRef") or {}
        history = (branch.get("target") or {}).get("history",{})
        commits = history.get("totalCount",0)
        pushed = (repo.get("pushedAt") or "")[:10]
        body += txt(32,y+55,f'{commits} commits no repo   /   push: {pushed}',19,MUTED)
        panel(f"project-{slug}.svg",y+113,"projetos/"+slug,body,title+". "+summary+" "+" ".join(lines),f'{branch.get("name","—")} / abrir repositório',GOLD)


def render_activity(user, stamp):
    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    weeks = calendar["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    active = sum(day["contributionCount"]>0 for day in days)
    body = ""
    metrics = [(calendar["totalContributions"],"contribuições"),(collection["totalCommitContributions"],"commits"),(active,"dias ativos")]
    for i,(number,label) in enumerate(metrics):
        x=32+i*307
        body += txt(x,111,number,42,INK)+txt(x,142,label,20,MUTED)
    body += txt(32,189,"Contribuições por mês",23,GOLD)
    monthly = monthly_counts(weeks)
    maximum = max((value for _,value in monthly),default=1) or 1
    for i,(month,value) in enumerate(monthly):
        x=38+i*75
        height=115*value/maximum
        body += rect(x,345-height,43,height,GREEN,3)
        body += txt(x+21,333-height,value,15,INK,'text-anchor="middle"')
        body += txt(x+21,370,month[5:]+"/"+month[2:4],14,MUTED,'text-anchor="middle"')
    body += txt(32,418,"Calendário de contribuições",22,GOLD)
    for col,week in enumerate(weeks):
        for day in week["contributionDays"]:
            row=(dt.date.fromisoformat(day["date"]).weekday()+1)%7
            count=day["contributionCount"]
            palette=["#253023","#365333","#557c43","#7aaa5c",GREEN]
            color=palette[0 if not count else min(4,1+(count-1)//3)]
            body += rect(32+col*17,443+row*18,13,14,color,2)
    body += txt(32,609,"Janela móvel de 12 meses / mês atual parcial",18,MUTED)
    panel("github-stats.svg",679,"atividade.git",body,"Estatísticas, evolução mensal e calendário de contribuições dos últimos 12 meses.",f"GitHub / {stamp}")


def render_languages(nodes,stamp):
    rows=distribution(nodes)
    body=txt(32,99,"Onde está meu código",29,INK,'font-weight="700"')
    x=32
    for i,(name,percent) in enumerate(rows):
        width=896*percent/100
        body+=rect(x,124,width,24,COLORS[i],0)
        x+=width
    for i,(name,percent) in enumerate(rows):
        x=32+(i%2)*470
        y=201+(i//2)*48
        body+=rect(x,y-15,13,13,COLORS[i],3)
        body+=txt(x+26,y,name,22,INK)
        body+=txt(x+419,y,f"{percent:.1f}%",21,COLORS[i],'text-anchor="end"')
    body+=txt(32,357,"Tamanho de código público / inclui arquivados",18,MUTED)
    panel("languages.svg",424,"linguagens.git",body,"Linguagens por bytes nos repositórios públicos, excluindo forks.",f"GitHub / {stamp}")


def render_waka(data,stamp):
    if not data:
        return
    total=duration(data.get("total_seconds"))
    body=txt(32,112,total,42,INK)
    body+=txt(32,146,"tempo registrado",21,MUTED)
    java=next((item for item in data.get("languages",[]) if item["name"]=="Java"),None)
    if java:
        body+=txt(540,112,duration(java.get("total_seconds")),36,GOLD)+txt(540,146,"tempo registrado em Java",20,MUTED)
    rows=data.get("languages",[])[:5]
    for i,item in enumerate(rows):
        y=211+i*49
        body+=txt(32,y,item["name"],22,INK)
        body+=rect(247,y-18,545,21,"#253023",3)
        body+=rect(247,y-18,max(1,545*item["percent"]/100),21,COLORS[i],3)
        body+=txt(924,y,f'{item["percent"]:.1f}%',21,COLORS[i],'text-anchor="end"')
    range_label="histórico completo" if data.get("range")=="all_time" else "período público selecionado"
    body+=txt(32,483,range_label+" / editores conectados",19,MUTED)
    panel("wakatime.svg",553,"tempo.waka",body,f"{total} registrados. Linguagens por tempo no WakaTime.",f"WakaTime / {stamp}",GOLD)


def readme(waka, periods=None):
    lines=[
        '<!-- Gerado a partir dos dados públicos. Textos e layout: scripts/render_profile.py. -->',
        '<p align="center"><img src="./assets/termux.svg" width="960" alt="Carvel, desenvolvimento backend com Java. Cabeçalho com estatísticas atuais do GitHub e WakaTime." /></p>',
        '<p align="center"><a href="https://lordcarvel.github.io/LordCarvel/#activity">Explorar atividade por período</a> &nbsp; / &nbsp; <a href="https://github.com/LordCarvel/Cdatra">Conhecer o Cdatra</a> &nbsp; / &nbsp; <a href="https://github.com/LordCarvel?tab=repositories">Todos os projetos</a></p>',
        '<p align="center"><img src="./assets/about.svg" width="960" alt="Sobre Carvel: foco em backend Java, persistência e aplicações para pedidos, entregas e caixa." /></p>',
        '<p align="center"><img src="./assets/stack.svg" width="960" alt="Tecnologias: Java 17, Node.js, JDBC, SQL, H2, SQLite, React, Electron, JUnit, Maven, JaCoCo, Git e Neovim." /></p>',
    ]
    for slug,title,summary,_,_ in PROJECTS:
        lines.append(f'<p align="center"><a href="https://github.com/LordCarvel/{slug}"><img src="./assets/project-{slug}.svg" width="960" alt="{escape(title)}: {escape(summary)} Abrir repositório." /></a></p>')
    lines += ['<a id="atividade-por-periodo"></a>',
        '<p align="center"><a href="https://lordcarvel.github.io/LordCarvel/#activity"><img src="./assets/explore.svg" width="960" alt="Explore a atividade por mês, bimestre, semestre ou ano no painel interativo." /></a></p>',
        '<p align="center">'+"\n".join(f'<a href="https://lordcarvel.github.io/LordCarvel/?period={key}#activity"><img src="./assets/filter-{key}.svg" width="22%" alt="Filtrar: {label}" /></a>' for key,label in (("mes","Mês"),("bimestre","Bimestre"),("semestre","Semestre"),("ano","Ano")))+'</p>',
    ]
    for key, period in (periods or {}).items():
        interval = f'{period["start"]} a {period["end"]}'
        lines.append(f'<details>\n<summary>{period["label"]} · {period["contributions"]} contribuições · {period["commits"]} commits</summary>\n\n<p align="center"><a href="https://lordcarvel.github.io/LordCarvel/?period={key}#activity"><img src="./assets/period-{key}.svg" width="960" alt="{period["label"]}, {interval}: {period["contributions"]} contribuições, {period["commits"]} commits e {period["active_days"]} dias ativos." /></a></p>\n\n</details>')
    lines += [
        '<p align="center"><img src="./assets/languages.svg" width="960" alt="Distribuição atual das linguagens pelo tamanho de código nos repositórios públicos." /></p>',
        '<!-- WAKATIME:START -->',
    ]
    if waka or (ROOT/"assets"/"wakatime.svg").exists():
        lines.append('<p align="center"><a href="https://wakatime.com/@639f7836-87c5-41ed-8dd2-0f0090178640"><img src="./assets/wakatime.svg" width="960" alt="Tempo de programação, tempo em Java e linguagens no período público do WakaTime." /></a></p>')
    lines += ['<!-- WAKATIME:END -->',
        '<p align="center"><a href="https://github.com/LordCarvel/Cdatra"><img src="./assets/review.svg" width="960" alt="Quer conhecer meu código? Comece pelo Cdatra para Java, API de persistência, testes e documentação. Veja o Easy Hub para uma aplicação com interface, servidor e desktop." /></a></p>',
        '<p align="center"><a href="https://github.com/LordCarvel/Cdatra#readme">Ler a documentação do Cdatra</a> &nbsp; / &nbsp; <a href="https://github.com/LordCarvel/EasyPrintV2">Explorar o Easy Hub</a> &nbsp; / &nbsp; <a href="https://lordcarvel.github.io/LordCarvel/">Ver minha atividade</a></p>',
        '<p align="center"><sub>Dados atualizados a cada 6 horas. Filtros: períodos de calendário em andamento. WakaTime: histórico público completo, independente dos filtros. Linguagens do GitHub: tamanho atual do código público, sem recorte de período.</sub></p>',
    ]
    (ROOT/"README.md").write_text("\n\n".join(lines).rstrip()+"\n",encoding="utf-8")


def render(user,nodes,waka,now,periods=None):
    stamp=now.strftime("%d/%m/%Y %H:%M -03")
    render_header(user,waka,stamp)
    render_about()
    render_stack()
    render_projects(nodes)
    render_activity(user,stamp)
    render_languages(nodes,stamp)
    render_waka(waka,stamp)
    from profile_views import publish_views
    publish_views(user,nodes,waka,now,periods or {})
    readme(waka,periods)
