from pathlib import Path
import subprocess,json,sys
R=Path(__file__).resolve().parent
W=R/'workspace'; P=R/'project'; A=R/'authored'; A.mkdir(exist_ok=True)
log=[]
def cli(*args,allowed=(0,)):
 p=subprocess.run([sys.executable,'-X','utf8','-m','strategist',*map(str,args)],cwd=W,capture_output=True,encoding='utf-8')
 log.append({'args':list(map(str,args)),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 (R/'workflow-log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
 if p.returncode not in allowed:raise RuntimeError(p.stdout+p.stderr)
 return p

def save(name,obj):
 p=A/(name+'.json');p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');return p
brief={'question':'Почему упал общий D30 и какой путь рекомендовать?','objective':'Выбрать проверяемую продуктовую и коммуникационную стратегию','recipient':'Владелец Смены','decision_owner':'Сценарный владелец, бизнес-выбор не одобрен','constraints':['30000 RUB','14 дней','нет внешних действий','только синтетические материалы','не обещать roadmap'],'success_metric':'Сегментный зрелый D30, активация, вклад после привлечения','data_available':['cohorts.csv','product.md','notes.md','request.md'],'data_classification':'public_or_own','next_question':'Вопросы недоступны; неизвестны каналы, повторная выручка, устранимые расходы.'}
cli('commit',P,'brief',save('brief',brief))
cli('approve',P,'brief','--by','Сценарный владелец','--reason','materials/request.md:6 подтверждает рамку, исключительно workflow; не бизнес-решение','--simulation')
claims=[]
for ident,source,line,description in [('capability','product',2,'В учебном продукте есть ручное расписание, повтор и приглашения.'),('roadmap','product',3,'Автопланирование не выпущено.'),('fixed','product',7,'Фиксированные затраты 40000 RUB/месяц, таблица не LTV.'),('ux','notes',3,'Два учебных сеанса не оценивают частоту проблемы.')]:
 quote=(R/'materials'/f'{source}.md').read_text(encoding='utf-8-sig').splitlines()[line-1]
 claim={'id':ident,'type':'demo_fact','text':description,'evidence':[{'source':source,'locator':f'line:{line}','quote':quote}],'confidence':'high','confidence_reason':'Точная строка учебного материала; вне сценария не подтверждено.'}
 cli('claim','add',P,save(ident,claim));claims.append(ident)
cli('analyze-cohorts',P,'--source','cohorts','--id','cohort-metrics')
cli('retrieve',P,'активация удержание приглашения')
research={'questions':[{'question':'Mix или ухудшение пути?','decision_impact':'Не переделывать весь onboarding без диагноза','method':'Зрелые когорты по сегментам и диагностика событий','status':'Описательный расчёт выполнен; причина неизвестна'}],'findings':[{'conclusion':'Общий D30 52→33%, в обоих сегментах +5 п.п.; команды активируются 80→20%. См. calculations.json и report.md.','claims':['ux'],'limits':'UX не доказывает причину; вычисления отдельно прослеживаются к cohorts.csv:2–5.'},{'conclusion':'Рекламный текст не соответствует функциям','claims':['capability','roadmap'],'limits':'Учебный снимок, нет рыночной проверки'}],'unknowns':[{'unknown':'Каналы, события, LTV, устранимые расходы','decision_impact':'Может изменить фокус или привести к закрытию','next_action':'Диагностика и финансовый сценарий до дня 14'}],'contradictions':['Общий D30 падает при росте внутрисегментного; обещание автопланирования противоречит roadmap.'],'stop_rule':'14 дней или 30000 RUB; неубедительный результат не разрешает расширение.'}
cli('commit',P,'research',save('research',research))
opts=[]
for ident,kind,name,audience,changes,econ,obs,val in [
 ('keep','status_quo','Статус-кво','Текущие аккаунты','Без развития и рекламы','40000/месяц сохраняются',['Потеря активации команд','Отрицательный вклад solo'],'Проверка измерений и зрелых когорт'),
 ('focus','focus','Диагностика команд','Команды до 20','Проверка текущего пути и точечный прототип','Потолок 30000, эффект неизвестен',['Причина может быть в канале','Потеря будущей ценности solo'],'Логи, до 8 UX, повторная выручка'),
 ('rewrite','other','Полный onboarding','Все аккаунты','Перестройка обучения','Стоимость неизвестна',['Дублирование существующего примера','Не решает качество потока'],'Сначала диагностика'),
 ('close','shutdown','Закрытие','Все текущие клиенты','Остановка развития и план выхода','Экономия устранимой части постоянных затрат минус стоимость выхода',['Потеря будущих потоков команд','Миграция и обязательства могут быть дороже'],'Трёхмесячное сравнение продолжения и выхода')]:
 opts.append(dict(id=ident,kind=kind,name=name,audience=audience,changes=changes,economics=econ,objections=obs,validation=val,claims=claims))
options={'options':opts,'comparison':'Общий горизонт финансового сценария три месяца; данных пока мало для числового рейтинга. Подробности report.md.','recommendation':'focus','why_not_others':'Сначала установить причину и стоимость обратимого шага; статус-кво оставляет активацию, переписывание не обосновано, закрытие преждевременно.','reversal_conditions':['Проблема событий или каналов — сохранять интерфейс','Устойчиво отрицательный будущий вклад и нет дешёвого восстановления — рассмотреть закрытие','Нет ясного результата на дне 14 — не масштабировать']}
cli('commit',P,'options',save('options',options))
cli('propose',P,'--option','focus','--rationale','Рекомендация условной диагностики; бизнес-выбор остаётся неодобренным, полный проект в report.md.','--claims',','.join(claims))
cli('audit',P,allowed=(0,1,2))
cli('export',P,'--draft',allowed=(0,))
cli('resume',P)
cli('context',P,'--max-chars','6000')
print('Workflow complete; decision proposed only.')
