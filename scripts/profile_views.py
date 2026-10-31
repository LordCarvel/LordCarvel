"""Period graphics and public data for the interactive profile."""

import json
import render_profile as base


def publish_views(user, nodes, waka, now, periods):
    stamp=now.strftime("%d/%m/%Y %H:%M -03")
    body=base.txt(32,103,"Meu código, ao longo do tempo.",33,base.INK,'font-weight="700"')
    body+=base.txt(32,146,"Escolha um período e explore os projetos em atividade.",23,base.MUTED)
    body+=base.txt(32,191,"Abrir painel interativo / mês · bimestre · semestre · ano",21,base.GREEN)
    base.panel("explore.svg",263,"atividade / selecionar período",body,"Abra o painel para filtrar contribuições, commits, dias ativos e projetos por período.","períodos de calendário / dados do GitHub")
    for key,label in (("mes","Mês"),("bimestre","Bimestre"),("semestre","Semestre"),("ano","Ano")):
        document=f'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="62" viewBox="0 0 220 62" role="img"><title>Filtrar: {label}</title>{base.rect(1,1,218,60,"#1b251b",8,"stroke=\"#53674c\"") }<text x="110" y="39" text-anchor="middle" font-family="Consolas,monospace" font-size="24" fill="{base.GREEN}">{label}</text></svg>'
        (base.ROOT/"assets"/f"filter-{key}.svg").write_text(document+"\n",encoding="utf-8")
    for key,period in periods.items():
        render_period(key,period,stamp)
    body=base.txt(32,102,"Quer conhecer meu código?",33,base.INK,'font-weight="700"')
    for y,line,color in [
        (151,"Comece pelo Cdatra: Java, persistência e testes.",base.GOLD),
        (190,"A API, os exemplos e os limites estão documentados.",base.MUTED),
        (246,"No Easy Hub, veja a aplicação completa:",base.GREEN),
        (285,"interface, servidor, impressão e versão desktop.",base.MUTED),
        (340,"Gosto de entender o problema antes de escrever a solução.",base.INK),
    ]:
        body+=base.txt(32,y,line,23,color)
    base.panel("review.svg",417,"continue-a-conversa.md",body,"Comece pelo Cdatra para conhecer meu trabalho em Java, persistência e testes. Explore o Easy Hub para interface, servidor e desktop.","código aberto / exemplos reais",base.GOLD)
    projects=[]
    by_name={node["name"]:node for node in nodes}
    for slug,title,summary,_,stack in base.PROJECTS:
        repo=by_name.get(slug)
        if not repo:
            continue
        branch=repo.get("defaultBranchRef") or {}
        commits=((branch.get("target") or {}).get("history") or {}).get("totalCount",0)
        projects.append({"name":slug,"title":title,"summary":summary,"url":f"https://github.com/LordCarvel/{slug}","stack":stack.split(" / "),"commits":commits,"pushed_at":repo.get("pushedAt")})
    data={"updated_at":now.isoformat(),"profile":{"name":"Carvel","role":"Desenvolvimento backend com Java","github":"https://github.com/LordCarvel","projects":projects},"periods":periods,
          "languages":[{"name":name,"percent":percent} for name,percent in base.distribution(nodes)]}
    site=base.ROOT/"site"
    site.mkdir(exist_ok=True)
    old_path=site/"data.json"
    if waka:
        data["wakatime"]={**waka,"updated_at":now.isoformat()}
    elif old_path.exists():
        data["wakatime"]=json.loads(old_path.read_text(encoding="utf-8")).get("wakatime")
    else:
        data["wakatime"]=None
    old_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def render_period(key,period,stamp):
    body=base.txt(32,100,period["label"],31,base.INK,'font-weight="700"')
    body+=base.txt(32,137,f'{period["start"]} a {period["end"]}',22,base.MUTED)
    for i,(number,label) in enumerate(((period["contributions"],"contribuições"),(period["commits"],"commits"),(period["active_days"],"dias ativos"))):
        x=32+i*306
        body+=base.txt(x,204,number,41,base.GREEN)+base.txt(x,239,label,21,base.MUTED)
    days=period["days"]
    # Calendar uses fixed day positions, preserving zero-activity dates.
    bins=[]
    size=max(1,(len(days)+29)//30)
    for start in range(0,len(days),size):
        chunk=days[start:start+size]
        bins.append((chunk[0]["date"],sum(day["count"] for day in chunk)))
    maximum=max((count for _,count in bins),default=1) or 1
    slot=896/max(1,len(bins))
    body+=base.txt(32,292,"Contribuições no período",23,base.GOLD)
    for i,(date,count) in enumerate(bins):
        height=110*count/maximum
        body+=base.rect(32+i*slot,430-height,max(2,slot-6),height,base.GREEN,2)
    body+=base.txt(32,467,"Abra o painel para explorar datas e repositórios.",21,base.MUTED)
    base.panel(f"period-{key}.svg",539,"atividade/"+key,body,f'{period["label"]}: {period["contributions"]} contribuições, {period["commits"]} commits e {period["active_days"]} dias ativos.',f"GitHub / {stamp}")
