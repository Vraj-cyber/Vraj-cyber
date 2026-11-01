"""Compose GitHub-safe SVG panels without external CSS, fonts, or image requests.

The calendar geometry comes directly from github-profile-3d-contrib output.
A camera transform flattens its viewing angle. A uniform vertical display scale
emphasizes nonzero columns without changing dates, counts, or relative heights.
"""
import base64
import datetime as dt
import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET

BG, CARD, BORDER = '#0B1521', '#11202D', '#284253'
ACCENT, FG, MUTED = '#67D8D4', '#F1F7FA', '#BED0DB'
FONT = 'ui-monospace,SFMono-Regular,Consolas,monospace'
ET.register_namespace('', 'http://www.w3.org/2000/svg')


def text(x, y, value, size=14, color=MUTED, weight=400, anchor='start', family=FONT):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


def box(x, y, w, h, fill=CARD, radius=9, stroke=BORDER):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def icon(kind, x, y, size=24, color=ACCENT):
    paths = {
        'repo': '<rect x="4" y="3" width="16" height="16" rx="2"/><path d="M8 19v3m8-3v3M8 16h8"/>',
        'star': '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8-6.2-3.2L5.8 21 7 14.2 2 9.3l6.9-1Z"/>',
        'branch': '<circle cx="6" cy="5" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="20" r="2"/><path d="M6 7v11m0-4c0-5 12-1 12-6"/>',
        'users': '<circle cx="9" cy="7" r="3"/><path d="M2 21v-3a7 7 0 0 1 14 0v3m0-17a3 3 0 0 1 0 6m3 4c3 1 3 4 3 7"/>',
        'calendar': '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M7 2v5m10-5v5M3 10h18"/>',
        'code': '<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18"/>',
        'folder': '<path d="M2 7V4h8l3 3h9v14H2Zm0 3h20"/>',
        'robot': '<rect x="3" y="7" width="18" height="14" rx="4"/><path d="M12 3v4m-5 6v2m10-2v2m-9 3h8M1 11v6m22-6v6"/><circle cx="12" cy="2" r="1"/>',
        'globe': '<circle cx="12" cy="12" r="10"/><ellipse cx="12" cy="12" rx="4" ry="10"/><path d="M2 12h20M4 6h16M4 18h16"/>',
        'leaf': '<path d="M3 21c0-10 4-16 18-18 0 13-5 18-14 16m-4 2L17 7"/>',
        'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="m12 12 9-9m-5 0h5v5"/>',
    }
    return f'<g transform="translate({x} {y}) scale({size/24})" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</g>'


def pill(x, y, label, width, color=ACCENT):
    return box(x, y, width, 28, '#0D1C29', 10) + text(x+width/2, y+18, label, 11, color, anchor='middle')


def svg(body, w, h, title, description):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">'
            f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>{body}</svg>\n')


def profile(data):
    # Clip the approved avatar artwork from the supplied reference using native SVG.
    avatar = base64.b64encode(Path('assets/avatar.png').read_bytes()).decode()
    result = box(1, 1, 998, 230, BG)
    result += '<defs><clipPath id="avatar"><circle cx="122" cy="124" r="89"/></clipPath></defs>'
    result += f'<g clip-path="url(#avatar)"><image href="data:image/png;base64,{avatar}" x="32" y="34" width="180" height="180"/></g>'
    result += '<circle cx="122" cy="124" r="90" fill="none" stroke="#67D8D4" stroke-width="1.5"/>'
    result += '<circle cx="191" cy="190" r="8" fill="#67D8D4" stroke="#0B1521" stroke-width="4"><animate attributeName="opacity" values=".65;1;.65" dur="5s" repeatCount="indefinite"/></circle>'
    result += text(257, 41, '@Vraj-cyber', 14, ACCENT)
    result += text(257, 87, 'V. Vrajesh', 41, FG, 650, family='Segoe UI,Arial,sans-serif')
    result += text(258, 115, 'AI · Bioengineering · Builder', 15, FG)
    result += text(258, 145, 'Exploring artificial intelligence and biology.', 13)
    result += text(258, 165, 'Building useful things, one idea at a time.', 13)
    for x, label, width in [(258,'Python',87),(354,'AI / ML',87),(450,'Bioengineering',142),(601,'Web Dev',99)]:
        result += pill(x,180,label,width)
    result += '<path d="M721 23V211" stroke="#284253"/>'
    for i, (key,label,kind) in enumerate([
        ('public_repositories','Repositories','repo'),('stars_received','Total stars','star'),
        ('contributions_last_year','Contributions','branch'),('followers','Followers','users')]):
        y=46+i*48
        result += icon(kind,748,y-16,21) + text(786,y,label,12) + text(964,y+1,f"{data[key]:,}",20,ACCENT,anchor='end')
        if i<3: result += f'<path d="M748 {y+18}H964" stroke="#1A3343"/>'
    return result


def contribution(data):
    root=ET.parse('profile-3d-contrib/profile-night-green.svg').getroot()
    calendar=next(c for c in root if c.tag.endswith('}g'))
    # Retain all 365 original days. Magnify the height above the zero baseline
    # uniformly, keeping the original relative contribution encoding intact.
    import re
    for day in calendar:
        for child in list(day):
            if child.tag.endswith('}animateTransform'):
                day.remove(child)
        sides=[c for c in day if 'cont-left-' in c.get('class','') or 'cont-right-' in c.get('class','')]
        if sides:
            old=float(sides[0].get('height'))
            new=2.6+6*(old-2.6)
            if old>2.6:
                xy=re.fullmatch(r'translate\(([-.0-9]+) ([-.0-9]+)\)',day.get('transform',''))
                if not xy: raise ValueError('Unexpected upstream calendar transform')
                day.set('transform',f'translate({xy[1]} {float(xy[2])-(new-old)*1.15:.2f})')
            for side in sides:
                side.set('height',f'{new:.2f}')
                for child in list(side):
                    if child.tag.endswith('}animate'):side.remove(child)
    # The calendar uses a teal palette and a low, wide camera angle.
    palette=[('#173D48','#102E39','#0D2631'),('#227C80','#1C626A','#174D59'),('#2CB5AF','#238D90','#1B717A'),('#41D6C6','#2CAEAA','#258B92'),('#67EBDD','#41C7BE','#2AA29F')]
    styles=''.join(f'.cont-{side}-{i}{{fill:{color}}}' for i,colors in enumerate(palette) for side,color in zip(['top','left','right'],colors))
    result=box(1,1,998,210,BG)+f'<style>{styles}</style>'
    result+=icon('calendar',23,16,23)+text(65,29,'GitHub Contributions',16,FG,600)
    result+=text(65,52,f"{data['contributions_last_year']:,} contributions in the last year",13,ACCENT)
    result+=text(751,30,'Less',10)
    for i,c in enumerate(palette): result+=box(793+i*14,20,11,11,c[0],2,c[0])
    result+=text(877,30,'More',10)
    result+=f'<g transform="matrix(.74 -.3175 0 .55 30 42)">{ET.tostring(calendar,encoding="unicode")}</g>'
    end=dt.datetime.strptime(data['updated_utc'],'%Y-%m-%d %H:%M UTC').date()
    start=end-dt.timedelta(days=364)
    for i in range(12):
        month_index=start.month-1+i
        day=dt.date(start.year+month_index//12,month_index%12+1,1)
        x=134+max(0,(day-start).days)/7*14.8
        result+=text(round(x,1),194,day.strftime('%b'),10,'#819EAF',anchor='middle')
    result+=text(970,194,'Height emphasis ×6',8,'#819EAF',anchor='end')
    result+=text(970,207,f'{start:%d %b %Y} – {end:%d %b %Y}',8,'#819EAF',anchor='end')
    return result


def languages(data):
    result=box(1,1,444,262,BG)+icon('code',23,17,24)+text(66,36,'Languages &amp; Technologies'.replace('&amp;','&'),16,FG,600)
    counts=data['language_bytes_public_nonfork']; total=sum(counts.values())
    colors=['#28B6D5','#FFD05D','#FF8F66','#A27AF7','#7897AD']
    for i,(name,count) in enumerate(list(counts.items())[:5]):
        y=76+i*31; value=count/total if total else 0
        label='<0.1%' if 0<value<.001 else f'{value:.1%}'
        result+=f'<circle cx="30" cy="{y-4}" r="6" fill="{colors[i]}"/>'
        result+=text(48,y,name,13)+box(142,y-10,224,11,'#152F3D',5,'#152F3D')
        if value: result+=box(142,y-10,max(1,224*value),11,colors[i],5,colors[i])
        result+=text(422,y,label,11,anchor='end')
    result+=text(24,210,'Public code bytes · owned non-fork repos',11,'#819EAF')
    result+='<path d="M24 223H421" stroke="#1A3343"/>'
    result+=text(24,245,'Skills / interests',11,ACCENT)+text(181,245,'Python · AI · Biology',11)
    return result


def projects():
    result=box(1,1,542,262,BG)+icon('folder',20,17,24)+text(62,36,'Featured Work',16,FG,600)
    cards=[(13,49,'robot','Nova assistant',['Local + cloud personal AI.','Ongoing development.'],['Python','AI','LLM']),
           (278,49,'globe','Portfolio website',['Personal work & background.','Public source available.'],['JavaScript','Web']),
           (13,154,'leaf','BODY//CONTROL',['Systems biology through play.','Ongoing development.'],['Systems','Learning']),
           (278,154,'target','Current focus',['AI, bioengineering & tools.','Exploring and building.'],['AI','Biology'])]
    for x,y,kind,title,lines,tags in cards:
        result+=box(x,y,251,96,CARD,9)+box(x+9,y+11,36,36,'#0A2A37',9,'#163B49')+icon(kind,x+16,y+18,23)
        result+=text(x+60,y+23,title,12,ACCENT,600)
        result+=text(x+60,y+43,lines[0],9.5)+text(x+60,y+58,lines[1],9.5)
        tx=x+60
        for tag in tags:
            w=len(tag)*5.3+14
            result+=box(tx,y+69,w,18,'#0D1C29',7)+text(tx+w/2,y+81,tag,8.5,anchor='middle')
            tx+=w+5
    return result


def main():
    data=json.loads(Path('assets/stats.json').read_text())
    panels={'profile-card.svg':(profile(data),1000,232,'V. Vrajesh · profile and live metrics'),
            'contributions.svg':(contribution(data),1000,212,'Real GitHub contribution calendar'),
            'languages.svg':(languages(data),446,264,'Public code languages and interests'),
            'projects.svg':(projects(),544,264,'Featured work and truthful project statuses')}
    description='GitHub API snapshot: '+data['updated_utc']+'. Public metrics; language bytes are not proficiency.'
    for name,(body,w,h,title) in panels.items(): Path('assets',name).write_text(svg(body,w,h,title,description))
    # Preserve stats.svg as an independently usable compact metrics/profile card.
    Path('assets/stats.svg').write_text(Path('assets/profile-card.svg').read_text())
    body=f'<rect width="1000" height="732" fill="{BG}"/>'+panels['profile-card.svg'][0]
    body+='<g transform="translate(0 244)">'+panels['contributions.svg'][0]+'</g>'
    body+='<g transform="translate(0 468)">'+panels['languages.svg'][0]+'</g>'
    body+='<g transform="translate(456 468)">'+panels['projects.svg'][0]+'</g>'
    Path('assets/dashboard.svg').write_text(svg(body,1000,732,'V. Vrajesh · engineering dashboard',description))
    print('Rendered dashboard and modular panels from current GitHub data and original 3D geometry')


if __name__=='__main__': main()
