import sys,json
for l in sys.stdin:
  try: r=json.loads(l)
  except: print(l,end=''); continue
  print(r['task'],r['tool'][:18].ljust(18),r['mode'][:10].ljust(10),r['out_tokens'],r['cmd_chars'],r['rc'],r['answer_right'],r['exit_code_right'],r['seconds'],r['found'])
