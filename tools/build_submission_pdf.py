"""Build the designed submission PDF. Authoring-only dependencies: reportlab, Pillow.

Run from any directory with the authoring Python environment. To match the
submission, set STRATEGIST_FONT_DIR to static Unbounded and Manrope faces
named in pdf_theme.py. The default Windows build uses Segoe UI and Consolas.
The agent and offline demo do not require these authoring dependencies.
"""

import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from pdf_theme import (
    BRIGHT, CORAL, EDGE, FEATURE, LILAC, MUTED, PAGE, PANEL, PANEL_ALT, PINK,
    TEXT, page_art, register_fonts,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STRATEGIST_PDF_OUTPUT', ROOT/'docs'/'contest-description.pdf'))
FONTS = Path(os.environ.get('STRATEGIST_FONT_DIR', 'C:/Windows/Fonts'))
register_fonts(FONTS)

W, H = 595.276, 841.89
M, CW = 45, W-90

test_data = json.loads((ROOT/'docs'/'verification-v0.6.json').read_text(encoding='utf-8'))
bench = json.loads((ROOT/'docs'/'checkpoint-benchmark.json').read_text(encoding='utf-8'))
case = json.loads((ROOT/'examples'/'public-case'/'state.json').read_text(encoding='utf-8'))
pilot_trace = json.loads((ROOT/'examples'/'telecom-brief'/'demo-run'/'trace.json').read_text(encoding='utf-8'))
pilot_cli_seconds = f"{pilot_trace['elapsed_seconds']:.2f}".replace('.', ',')
video = json.loads((ROOT/'docs'/'submission-video.json').read_text(encoding='utf-8'))
video_seconds = round(video['duration_seconds_approx'])
video_duration = f'{video_seconds//60}:{video_seconds%60:02d}'
test_count = test_data['test_count']
old_bytes = bench['summary']['separate']['median_stdout_utf8_bytes']
new_bytes = bench['summary']['checkpoint']['median_stdout_utf8_bytes']
reduction = 100*bench['stdout_reduction_fraction']

c = canvas.Canvas(str(OUT), pagesize=(W,H), pageCompression=1, pdfVersion=(1,4))
c.setTitle('Стратег Фабрики продуктов | описание проекта')
c.setAuthor('Команда проекта')
c.setSubject('Архитектура, доказательства, демонстрация и границы агентной системы')
layout = []


def col(value):
    return colors.HexColor(value)


def rect(x, top, w, h, fill, radius=0, stroke=None):
    c.setFillColor(col(fill))
    if stroke:
        c.setStrokeColor(col(stroke)); c.setLineWidth(.7)
    if radius:
        c.roundRect(x,H-top-h,w,h,radius,fill=1,stroke=bool(stroke))
    else:
        c.rect(x,H-top-h,w,h,fill=1,stroke=bool(stroke))


def line(x1,y1,x2,y2,color=EDGE,width=.7):
    c.setStrokeColor(col(color));c.setLineWidth(width)
    c.line(x1,H-y1,x2,H-y2)


def para(text,x,top,w,size=10.2,leading=None,color=TEXT,font='UI',max_h=None):
    text=text.replace('\u2011','-').replace('—','-').replace('–','-')
    style=ParagraphStyle('p',fontName=font,fontSize=size,leading=leading or size*1.43,textColor=col(color),splitLongWords=False)
    p=Paragraph(text,style);_,h=p.wrap(w,H)
    if max_h is not None and h>max_h+.1:
        raise ValueError(f'Box overflow: {text[:65]} ({h:.1f} > {max_h})')
    if top+h>H-18 or (top<790 and top+h>785):
        raise ValueError(f'Page overflow: {text[:65]}')
    p.drawOn(c,x,H-top-h)
    layout.append({'page':c.getPageNumber(),'x':x,'y':top,'w':w,'h':h,'text':text})
    return top+h


def label(text,x,top,color=MUTED,size=8.1):
    return para(text,x,top,min(CW,W-M-x),size=size,leading=size*1.25,color=color,font='UIB')


def footer(page,section):
    ink=MUTED
    line(M,790,W-M,790,EDGE)
    para('СТРАТЕГ / ФАБРИКА ПРОДУКТОВ',M,802,255,7.1,color=ink,font='UIB')
    para(section,W-225,802,150,7.1,color=ink)
    para(f'{page:02d}',W-61,799,25,10,color=LILAC,font='Mono')


def page_start(page,section,title,deck=None):
    page_art(c,W,H,page)
    label(section.upper(),M,39,PINK)
    title_lines=title.split('<br/>')
    title_width=max(pdfmetrics.stringWidth(part,'Display',28) for part in title_lines)
    title_size=min(28,28*(CW-8)/title_width)
    end=76
    for i,title_line in enumerate(title_lines):
        end=para(title_line,M,end,CW,title_size,37.5,BRIGHT if i==0 else LILAC,'Display')
    if deck:
        end=para(deck,M,end+13,CW,10.5,15,MUTED)
    footer(page,section)
    c.bookmarkPage('page'+str(page));c.addOutlineEntry(section,'page'+str(page),level=0)
    return end


def step_number(n,x,top):
    rect(x,top,27,27,FEATURE,5,EDGE)
    para(str(n).zfill(2),x+6,top+5,25,10,color=PINK,font='UIB')


def arrow(x1,y,x2,color=PINK):
    line(x1,y,x2,y,color,1)
    line(x2-4,y-3,x2,y,color,1);line(x2-4,y+3,x2,y,color,1)


def card(x,top,w,h,tag,title,body,selected=False):
    bg=FEATURE if selected else PANEL
    rect(x,top,w,h,bg,9,stroke=EDGE)
    if selected:
        rect(x+1,top+13,2,h-26,PINK,1)
    label(tag,x+17,top+15,LILAC if selected else MUTED,7.5)
    end=para(title,x+17,top+37,w-34,16,20,BRIGHT if selected else TEXT,'UIB',max_h=43)
    para(body,x+17,end+8,w-34,9.5,13.7,MUTED,max_h=h-(end-top)-18)


# 01. Cover: title, argument, vector evidence cycle, factual status.
page_art(c,W,H,1,cover=True)
label('ИИ-ПРОЕКТ / ЗАДАНИЕ МЕГАФОНА',M,42,LILAC,8.5)
rect(W-102,37,57,22,PANEL_ALT,11)
para('v0.6',W-87,41,45,9,color=LILAC,font='UIB')
para('Стратег<br/>Фабрики',M,92,CW,51,61,BRIGHT,'Display')
para('продуктов',M,214,CW,51,61,PINK,'Display')
para('Что изменит решение?<br/>Какую проверку провести?<br/>Когда остановиться?',M,310,440,17,25,TEXT,'UIL')
para('Папка агента для работы в IDE с LLM',M,423,440,11,color=LILAC)
rect(M,484,CW,179,PANEL,14)
label('ЛОГИКА ДОКАЗАТЕЛЬСТВ',M+20,504,MUTED,8)
xs=[M+43+i*(CW-86)/4 for i in range(5)]
names=['Источник','Вывод','Вариант','Решение','Проверка']
for i,x in enumerate(xs):
    if i<4: arrow(x+12,553,xs[i+1]-12,LILAC)
    c.setFillColor(col(LILAC if i in (0,3) else PINK))
    c.circle(x,H-553,6,fill=1,stroke=0)
    para(names[i],x-35,572,76,8.7,color=BRIGHT,font='UIB')
path=c.beginPath();path.moveTo(xs[-1],H-608);path.curveTo(xs[-1],H-638,xs[0],H-638,xs[0],H-608)
c.setStrokeColor(col(LILAC));c.setLineWidth(.8);c.drawPath(path)
para('Новые данные возвращают решение на пересмотр',M+76,642,CW-120,8.4,color=MUTED)
line(M,701,W-M,701,EDGE)
for x,num,caption in [(M,str(test_count),'технических тестов'),(M+172,'2','решения Q1 / Q2'),(M+345,'7','MCP-инструментов')]:
    para(num,x,715,110,31,35,LILAC,'UIB')
    para(caption,x,754,160,8.4,color=MUTED)
footer(1,'Описание проекта')
c.showPage()


# 02. The value and criteria: four parallel blocks, no self-assigned grades.
page_start(2,'Ценность','Две стратегии.<br/>Одна логика решения.',
           'Агент помогает пройти путь от неоднозначного запроса до выбора, который можно проверить и пересмотреть.')
gap=16;cw=(CW-gap)/2
items=[('01 / ПРОРАБОТАННОСТЬ','Основания видны','Факты, гипотезы и прогнозы разделены. У существенных утверждений есть источник, цитата и границы применимости.'),
 ('02 / НЕЙРОТЕХНОЛОГИИ','Модель ведёт процесс','LLM формулирует развилки и критикует допущения. Три навыка и инструменты подключаются по задаче.'),
 ('03 / ИМПЛЕМЕНТАЦИЯ','Работу можно продолжить','Источники и состояние сохраняются отдельно от чата. Возобновление и пересмотр проверяются инструментами.'),
 ('04 / КАЧЕСТВО','Результат пригоден для выбора','Руководитель видит, что изменит выбор и оправдывает ли следующая проверка её затраты.')]
for i,(tag,title,body) in enumerate(items):
    card(M+(i%2)*(cw+gap),219+(i//2)*180,cw,164,tag,title,body)
label('КАК ПРИНИМАЕТСЯ РЕШЕНИЕ',M,603,PINK)
para('Несколько реальных путей,<br/>включая отказ от изменений.',M,630,315,22,28,TEXT,'UIB')
para('В каждом кейсе рассматриваются статус-кво, альтернативное направление и закрытие инициативы. У вариантов есть сильные возражения и условия проверки.',M+330,627,CW-330,9.5,14,MUTED)
line(M,716,W-M,716)
para('Продуктовая стратегия задаёт аудиторию, пользу и экономику. Коммуникационная стратегия обещает только то, что подтверждено продуктом.',M,731,CW,10.1,15,TEXT)
c.showPage()


# 03. Architecture: actual workflow and separated knowledge planes.
page_start(3,'Архитектура','Модель исследует.<br/>Инструменты проверяют.',
           'LLM работает в IDE. Python сохраняет основания, считает показатели и контролирует переходы между этапами.')
left_w=277;right_x=M+307;right_w=CW-307
label('ПРОЦЕСС',M,211,PINK);label('СЛОИ ЗНАНИЙ',right_x,211,PINK)
stages=[('Бриф','Цель, получатель, ограничения и данные.'),('Исследование','Вопросы, источники, расчёты и пробелы.'),('Варианты','Разные пути и сильные возражения.'),('Выбор','Рекомендация и решение владельца.'),('Стратегии','Продукт, коммуникация и проверка.'),('Сопровождение','Обязательства и условия пересмотра.')]
for i,(title,body) in enumerate(stages):
    y=240+i*67
    if i<5: line(M+13,y+28,M+13,y+66,EDGE,1)
    step_number(i+1,M,y)
    para(title,M+41,y-1,left_w-45,13.8,18,TEXT,'UIB')
    para(body,M+41,y+22,left_w-45,9.3,13.2,MUTED)
    if i in (0,3):
        para('ВЫБОР ЧЕЛОВЕКА',M+41,y+43,left_w-45,6.8,8.5,PINK,'UIB')
layers=[('Правила','AGENTS.md'),('Методика','knowledge/'),('Навыки','.agents/skills/'),('Материалы','project/blobs/'),('Состояние','state.json'),('Результаты','project/exports/')]
for i,(title,path) in enumerate(layers):
    y=240+i*67
    rect(right_x,y,right_w,55,PANEL,8,EDGE)
    para(title,right_x+13,y+9,right_w-25,10.1,14,TEXT,'UIB')
    para(path,right_x+13,y+30,right_w-25,8.6,11,MUTED,'Mono')
rect(M,674,CW,90,FEATURE,9,EDGE)
label('СВЯЗЬ МЕЖДУ СЕАНСАМИ',M+18,689,LILAC)
para('resume → context → retrieve → source',M+18,710,CW-36,11.3,15,BRIGHT,'Mono')
para('Компактное состояние, затем нужные основания по запросу. Прежний ответ агента не становится новым независимым фактом.',M+18,733,CW-36,8.7,12,TEXT,max_h=25)
c.showPage()


# 04. Submission case, grounded in the organizer's example.
page_start(4,'Демонстрация','Семейная связь.<br/>От пилота к решению.',
           'Пример брифа МегаФона. Вымышленный оператор выбирает первый сценарий и решает, стоит ли расширять охват после пилота.')
shot=ROOT/'docs'/'screenshots'/'family-pilot-card.png'
iw,ih=PILImage.open(shot).size
image_w=CW-24;image_h=min(image_w*ih/iw,213)
image_w=min(image_w,image_h*iw/ih)
rect(M,224,CW,257,PANEL,9,EDGE)
label('РЕАЛЬНЫЙ СНИМОК ЛОКАЛЬНОГО ОТЧЁТА',M+14,239,PINK,7.3)
c.drawImage(str(shot),M+12,H-263-image_h,width=image_w,height=image_h,mask='auto')
para('Полная версия  /  examples/telecom-brief/demo-run/review.html',M,490,CW,8.1,11,MUTED)
changes=[('Q1','Зафиксировать пилот','Один тариф. Семь дней. Порог снижения 3 п.п. План сохранён с хешем до импорта результата.'),
 ('Q2','Сверить основания','Первый срез проходит правило пользы. Аналитик обнаруживает 80 неизвестных исходов в плече сигнала.'),
 ('03','Пересмотреть выбор','Агент отзывает прежнее основание и блокирует выпуск старой карточки. Сначала восстановить исходы, затем решить вопрос охвата.')]
for i,(n,title,body) in enumerate(changes):
    y=522+i*73
    para(n,M,y,35,19,23,PINK,'UIL')
    para(title,M+44,y,CW-44,12,17,TEXT,'UIB')
    para(body,M+44,y+22,CW-44,9.3,13.3,MUTED,max_h=43)
para('Входные показатели и наблюдения учебные. Согласование Q1 сыграно в сценарии. Решение Q2 ожидает владельца.',M,751,CW,8.1,11.5,MUTED,max_h=25)
c.showPage()


# 05. The options are meaningful, then product and communication align.
page_start(5,'Стратегический выбор','Четыре варианта.<br/>Осознанный выбор.',
           'Пилот проверяет своевременный сигнал и существующее выделение интернета на одном совместимом тарифе.')
alts=[('A / СТАТУС-КВО','Обычное обслуживание','Организатор проверяет остаток вручную. При низком остатке помощь может запоздать.',False),
      ('B / ПИЛОТ Q1','Сигнал и ручное действие','Ссылка открывает существующее выделение. Проверяем, хватает ли времени до ограничения.',True),
      ('C / РАЗРАБОТКА','Семейный кабинет','Меньше переходов, но больше затрат и прав доступа. Сравнить отдельно с проверенным сигналом.',False),
      ('D / ОСТАНОВКА','Закрыть инициативу','Оставить текущее обслуживание. Освободить ресурс, если нет безопасного или окупаемого пути.',False)]
for i,(tag,title,body,chosen) in enumerate(alts):
    card(M+(i%2)*(cw+gap),218+(i//2)*153,cw,139,tag,title,body,chosen)
label('ПРОДУКТ И ОБЕЩАНИЕ',M,541,PINK)
line(M,561,W-M,561)
para('Продукт',M,578,91,12,color=PINK,font='UIB')
para('Семьи с общим пакетом, совместимостью тарифа и действующим согласием участника. Сигнал ведёт к ручному действию.',M+103,575,CW-103,10,14.7,TEXT,max_h=47)
line(M,630,W-M,630)
para('Сообщение',M,646,91,12,color=PINK,font='UIB')
para('На подходящем тарифе можно выделить интернет из свободной части общего пакета. Право и остаток проверяются перед выдачей.',M+103,643,CW-103,10,14.7,TEXT,max_h=47)
rect(M,710,CW,59,PANEL_ALT,9)
para('Проверка',M+15,722,80,10.7,color=PINK,font='UIB')
para('Сравнение с обычным обслуживанием. 1 638 семей на плечо при учебной доле 12% и пороге 3 п.п. Семь дней на исход.',M+103,720,CW-119,9.2,13,MUTED,max_h=40)
c.showPage()


# 06. A falsifiable recommendation, with an open finite scenario matrix.
page_start(6,'Лаборатория решений','Что заставит нас<br/>изменить выбор?',
           'Сценарная проверка соединяет исследование с действием. Агент ищет развилки, инструмент считает цену ошибки, владелец принимает решение.')
label('КОМАНДНЫЙ ДИСК / УЧЕБНЫЕ ДОПУЩЕНИЯ',M,217,PINK,8)
rect(M,242,CW,79,FEATURE,9,EDGE)
para('Ограничить пилот командами',M+18,257,CW-36,20,26,BRIGHT,'UIB')
para('Кандидат при неизвестном сценарии; критерий - меньшая худшая цена ошибки.',M+18,291,CW-36,9,13,TEXT)
headers=['Сценарий','Сохранить','Пилот','Масштаб','Закрыть']
col_x=[M+10,M+198,M+273,M+347,M+427]
col_w=[179,70,68,74,67]
for i,txt in enumerate(headers):para(txt,col_x[i],347,col_w[i],8.2,11,MUTED,'UIB')
rows=[('Широкий спрос','20','60','100','0',3),('Только команды','5','45','10','0',2),
      ('Недостаточная польза','-10','-20','-70','0',4),('Расходы недооценены','-25','-35','-110','-5',4)]
for j,row in enumerate(rows):
    y=374+j*41
    rect(M,y-5,CW,38,PANEL if j%2==0 else PANEL_ALT,5)
    for i,txt in enumerate(row[:5]):
        if i==row[5]:rect(col_x[i]-5,y-1,57,26,FEATURE,5)
        para(txt,col_x[i],y+4,col_w[i],9.3,13,PINK if i==row[5] else TEXT,'UIB' if i==row[5] else 'UI')
para('Тысячи условных RUB за 8 недель. Выделен лучший допустимый вариант внутри сценария. Все числа придуманы для проверки метода, не выведены из реальных продаж.',M,550,CW,8.5,12.5,MUTED,max_h=40)
line(M,609,W-M,609)
para('105 000',M,628,227,32,37,CORAL,'UIB')
para('40 000',M+270,628,220,32,37,PINK,'UIB')
para('Худшая цена ошибки при выборе масштабирования по одному благоприятному сценарию.',M,674,229,9.7,14,TEXT,max_h=59)
para('Худшая цена ошибки ограниченного пилота при сравнении всех четырёх сценариев.',M+270,674,CW-270,9.7,14,TEXT,max_h=59)
para('Это сравнение двух математических правил в авторской модели. Оно не доказывает экономию денег или превосходство LLM над обычным чатом.',M,748,CW,8.4,12,MUTED,max_h=28)
c.showPage()


# 07. The important correction: research may end without resolving uncertainty.
page_start(7,'Критика исследования','Проверка тоже<br/>может не дать ответа.',
           'Агент должен проверить не только стратегию, но и собственное предложение «давайте проведём исследование».')
card(M,214,cw,182,'ДО КРИТИКИ','Идеальная диагностика','Проверка различает сценарии. Остаточная цена ошибки равна нулю; прямые расходы и задержка - 12 000 условных RUB.',True)
card(M+cw+gap,214,cw,182,'ПОСЛЕ КРИТИКИ','Возможен неясный ответ','Добавлен исход, совместимый со всеми сценариями. Неопределённость остаётся; расходы всё равно оплачены.')
label('ГРАНИЦА ЦЕНЫ ОШИБКИ С УЧЁТОМ РАСХОДОВ',M,425,PINK,7.8)
for i,(txt,value,fill) in enumerate([('Действовать сейчас',40000,LILAC),('Идеальная проверка',12000,PINK),('Есть неубедительный исход',52000,CORAL)]):
    y=452+i*55
    para(txt,M,y,360,9.5,13,TEXT)
    rect(M,y+22,CW-90,10,PANEL_ALT,4)
    rect(M,y+22,(CW-90)*value/52000,10,fill,4)
    para(f'{value:,}'.replace(',',' '),M+CW-78,y+16,80,12,16,TEXT if i==0 else fill,'UIB')
rect(M,643,CW,88,PANEL_ALT,10)
para('Вывод изменился',M+16,658,CW-32,14,19,PINK,'UIB')
para('Гарантированное улучшение выбора такой проверкой не подтверждается. Возможная польза остаётся неизвестной без оценки качества диагностики и вероятностей.',M+16,685,CW-32,9.5,13.5,TEXT,max_h=39)
para('Воспроизводится: demo/lab.py. Интерактивно: examples/decision-lab/exports/decision-lab.html. Расчёт связан с основаниями; новые данные требуют его пересмотра.',M,748,CW,8.2,11.8,MUTED,max_h=28)
c.showPage()


# 08. Engineering evidence, with the limits adjacent to the measured data.
page_start(8,'Доказательства','Проверено.<br/>С границами применимости.')
rect(M,190,150,112,FEATURE,9,EDGE)
para(str(test_count),M+18,201,125,45,50,LILAC,'UIB')
para('технических тестов<br/>пройдены',M+18,259,126,9.3,13,BRIGHT)
para('Что проверяют тесты',M+174,192,CW-174,13.5,18,TEXT,'UIB')
para('Цитаты, согласования, отзыв источников, перенос, MCP и HTML. Пилот: пропуски, незрелое окно, подмена порога, критические случаи, экономика и отзыв.',M+174,220,CW-174,10.1,14.5,MUTED,max_h=81)
label('СЛУЖЕБНЫЕ ОТВЕТЫ НА СОХРАНЕНИЕ',M,329,PINK)
para(f'{reduction:.1f}%'.replace('.',','),M,354,180,40,45,PINK,'UIB')
para('меньше UTF-8 байтов<br/>в служебных ответах CLI',M+185,363,CW-185,12.4,18,TEXT)
bar_x=M;bar_w=CW-70
for idx,(name,value,color) in enumerate([('Отдельное сохранение / 9 вызовов CLI',old_bytes,LILAC),('Атомарный checkpoint / 1 вызов CLI',new_bytes,PINK)]):
    y=428+idx*53
    para(name,bar_x,y,CW,8.8,12,MUTED)
    rect(bar_x,y+20,bar_w,11,PANEL_ALT,4)
    rect(bar_x,y+20,bar_w*value/old_bytes,11,color,4)
    para(f'{value:,}'.replace(',',' '),M+CW-62,y+16,70,10,13,TEXT,'UIB')
para('Три технических повтора каждого способа, одинаковые содержательные хеши. Медиана CLI: 1,620 с → 0,295 с. Это не замер полного ответа LLM, тарифицируемых токенов или качества стратегии.',M,542,CW,9.2,13.3,MUTED,max_h=43)
line(M,607,W-M,607)
label('ИЗМЕРЕНО',M,627,PINK);label('ОСТАЁТСЯ НЕИЗВЕСТНЫМ',M+270,627,CORAL)
para('В первой живой паре чат: 179 с; агент v0.3: 308 с. Преимущества скорости нет. Затем уменьшены служебные накладные расходы.',M,650,232,10,14.5,TEXT,max_h=75)
para('Полная цена модели и человека, выигрыш качества. Сравнение относится к v0.3 и одной задаче. Для v0.6 показан технический прогон.',M+270,650,CW-270,10,14.5,TEXT,max_h=75)
para('Проверено на Windows / Python '+test_data['python']+'. Структурный аудит не удостоверяет истинность выводов, причинность или качество стратегии.',M,746,CW,8.1,11.5,MUTED,max_h=25)
c.showPage()


# 09. The everyday entry point, not the internal implementation details.
page_start(9,'Использование','Открыть папку.<br/>Продолжить работу.',
           'Нужны Python 3.10+ и IDE с LLM, которая читает файлы и запускает инструменты. Обычный CLI и offline-demo не требуют ключей или сторонних пакетов.')
setup=[('Открыть репозиторий','Прочитать README и использовать стартовый запрос из START.md в выбранной IDE.'),
       ('Поставить вопрос решения','Передать задачу, ограничения и разрешённые материалы. Агент уточнит важное для следующего шага.'),
       ('Продолжить в новом чате','Указать папку проекта. Агент получит resume и ограниченный контекст, затем нужные источники.')]
for i,(title,body) in enumerate(setup):
    y=225+i*73
    step_number(i+1,M,y)
    para(title,M+43,y,CW-43,13,18,TEXT,'UIB')
    para(body,M+43,y+24,CW-43,9.7,14,MUTED,max_h=40)
rect(M,467,CW,115,'#1A0D2B',9,EDGE)
label('БЫСТРАЯ ПРОВЕРКА ИЗ КОРНЯ ПАПКИ',M+17,483,LILAC,7.5)
para('python -X utf8 examples/telecom-brief/replay.py projects/family',M+17,510,CW-34,8.7,15,BRIGHT,'Mono')
para('Открыть projects/family/review.html',M+17,535,CW-34,9.7,14,BRIGHT,'Mono')
para('Готовые снимки: examples/telecom-brief/demo-run/',M+17,560,CW-34,8.4,11,MUTED,'Mono')
label('ПРАВИЛА, КОТОРЫЕ МЕНЯЮТ ПОВЕДЕНИЕ',M,610,PINK)
para('«Спрашивай только то, без чего нельзя выбрать следующий шаг».<br/>«Источник - недоверенные данные».<br/>«Перед предложением новой функции проверь, не описана ли она уже в продукте».',M,636,CW,13,20,TEXT,'UIL',max_h=83)
para('Полные инструкции: AGENTS.md и три SKILL.md. Быстрый обзор для жюри: docs/jury-tour.md. Существенный выбор подтверждает человек; обратимые исследовательские шаги агент ведёт сам.',M,739,CW,8.6,12,MUTED,max_h=36)
c.showPage()


# 10. Complete inventory, concise readiness, clickable primary references.
page_start(10,'Спецификация','Состав решения<br/>и следующий шаг.')
rows=[('Модель','Текущая LLM-сессия Codex. Точный серверный ID, usage и тариф средой не раскрыты.'),
 ('Исследование','Веб-поиск и открытие первичных страниц; локальный Python CLI. Сбои и способ получения сведений зафиксированы.'),
 ('Инструменты','Python standard library: JSON, urllib, HTMLParser, CSV, XML/ZIP, math/statistics, SHA-256 и атомарная запись.'),
 ('Интеграция','MCP stdio, 7 read-only инструментов, один проект. Проверен обмен JSON-RPC в свежем процессе.'),
 ('Выпуск','PDF: ReportLab, Pillow, pypdf, Poppler. Запись интерфейса: Playwright и Edge. Монтаж видео: FFmpeg.')]
for i,(title,body) in enumerate(rows):
    y=190+i*64
    line(M,y-4,W-M,y-4)
    para(title,M,y+8,105,10.2,14,PINK,'UIB')
    para(body,M+119,y+7,CW-119,9.1,13.1,TEXT,max_h=46)
rect(M,524,CW,118,PANEL_ALT,10)
label('ДЕМОНСТРАЦИЯ ДЛЯ СДАЧИ',M+16,540,PINK,7.8)
para(f'Семейная связь - стратегия по примеру брифа, пилот Q1, пауза и решение Q2 после сверки. Видео {video_duration}. Исходники и команды для повторения входят в репозиторий.',M+16,563,CW-32,10.1,14.4,TEXT,max_h=48)
para('Видео показывает работу с HTML-отчётами и вывод фактического CLI-прогона. Наблюдения пилота синтетические.',M+16,610,CW-32,8.1,11.5,MUTED,max_h=27)
label('ПЕРВИЧНЫЕ ИСТОЧНИКИ И ПРОВЕРКИ',M,666,PINK,7.7)
refs=[('S1','Mozilla: активация и действующий onboarding','https://support.mozilla.org/en-US/kb/activate-firefox-relay-mask-your-email-address'),
      ('S2','Mozilla: назначение и создание масок','https://support.mozilla.org/en-US/kb/create-email-mask-through-firefox-relay'),
      ('S3','Mozilla: условия Firefox Relay для iOS','https://support.mozilla.org/en-US/kb/relay-masks-ios')]
for i,(sid,title,url) in enumerate(refs):
    para(f'<b>{sid}</b> / <link href="{url}" color="{PINK}">{escape(title)}</link>',M,687+i*19,CW,8.1,11.5,MUTED)
para('Материалы S1-S3 относятся к дополнительному кейсу Firefox Relay. Метод пилота: docs/pilot.md. Проверки: verification-v0.6.json и pilot-browser-verification.json.',M,748,CW,7.9,11,MUTED,max_h=24)
c.showPage()

# 11. Submission case: observed result, trace, and measured time.
page_start(11,'Чтение пилота','80 исходов меняют<br/>вывод о пользе.',
           'В срезе 1 700 семей на плечо. При сверке выяснилось, что результат 80 семей в плече сигнала неизвестен.')
gap=14; width=(CW-gap)/2
card(M,210,width,121,'ПО ИЗВЕСТНЫМ ИСХОДАМ','+3,05 п.п.','Снижение по 1 620 известным исходам в плече сигнала относительно контроля.',True)
card(M+width+gap,210,width,121,'ПО ВСЕМ НАЗНАЧЕННЫМ','−1,24…+3,47 п.п.','Крайние заполнения 80 пропусков. Данные допускают рост ограничений.')
label('СНИМОК ГРАФИКА ИЗ ОТЧЁТА',M,351,PINK,7.6)
shot=ROOT/'docs'/'screenshots'/'family-pilot-plot.png'
iw,ih=PILImage.open(shot).size
img_h=CW*ih/iw
c.drawImage(str(shot),M,H-377-img_h,width=CW,height=img_h,mask='auto')
end=para('Решение владельцу',M,512,CW,15,21,PINK,'UIB')
para('Сохранить охват. Сверить 80 исходов и повторить анализ с тем же планом. Финансисту проверить оплаченные месяцы и смету. Инцидент доступа или двойного списания потребует паузы.',M,end+10,CW,10.2,14.5,TEXT,max_h=60)
end=para('Экономика следующего охвата',M,618,CW,15,21,PINK,'UIB')
para('279,105 млн ₽ - годовой прогноз при допущениях, 5,895 млн ₽ до цели. Польза за 7 дней не устанавливает число оплаченных месяцев. Смета и вклад подтверждаются отдельно.',M,end+10,CW,10.2,14.5,TEXT,max_h=55)
para(f'Технический прогон: {len(pilot_trace["commands"])} команд за {pilot_cli_seconds} с. Журнал сохраняет отказ выдачи старой карточки и новую ревизию. Время модели и человека в этом кейсе не измерено.',M,734,CW,8.5,12,MUTED,max_h=44)
c.showPage()
c.save()

OUT.with_name('pdf-layout-map.json').write_text(json.dumps({'pages':11,'text_boxes':layout},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pdf':str(OUT),'pages':11,'text_boxes':len(layout),'design':'violet / pink, vector folds'},ensure_ascii=False))
