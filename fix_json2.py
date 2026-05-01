import json
p = r'v:\TRPG\trpg_orchestrator\outbox\chatgpt_raw_output.md'
t = open(p, 'r', encoding='utf-8').read()
t = t.replace('\u201c', "'").replace('\u201d', "'")
t = t.replace("低声开口：'这股味儿旧。风口那边翻过土，没新吼声。'", '低声开口：\\"这股味儿旧。风口那边翻过土，没新吼声。\\"')
t = t.replace("挤出一句：'再停，箱子底就泡了。'", '挤出一句：\\"再停，箱子底就泡了。\\"')
t = t.replace("护卫听见，'留半个车身的距离。'", '护卫听见，\\"留半个车身的距离。\\"')
open(p, 'w', encoding='utf-8').write(t)
data = json.load(open(p, 'r', encoding='utf-8'))
print('OK blocks=%d' % len(data['blocks']))
