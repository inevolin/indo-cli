import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
R=[r for r in json.load(open('results.json')) if r['task']!='T0']
def get(t, tool, mode=None):
    for r in R:
        if r['task']==t and r['tool']==tool and (mode is None or r['mode']==mode): return r
tasks=[("T1","Which repos are dirty?","naive loop","expert loop"),
       ("T2","Fetch all. Which are behind?","naive loop","expert loop"),
       ("T3","Which tests failed?","naive loop","expert loop"),
       ("T4","Which tests failed? (8 jobs)","xargs -P","expert GNU parallel"),
       ("T5","Find every TODO","naive grep -r","ripgrep --hidden"),
       ("T6","Who uses an old ava?","naive loop","grep with glob"),
       ("T7","Who is not on main?","naive loop","expert loop")]
rows=[]
for t,label,naive,expert in tasks:
    rows.append((label, get(t,naive), get(t,"old indo-cli"), get(t,expert), get(t,"new indo-cli","agent")))
RED="#d64545"; GREEN="#2e9e5b"; GRAY="#b8bec6"; DARK="#6b7480"
series=[("Plain loop or default", 1, RED),("Old indo-cli",2,GRAY),("Expert shell",3,DARK),("New indo-cli, short output",4,GREEN)]
fig,(a1,a2)=plt.subplots(1,2,figsize=(13,5.6),gridspec_kw={"width_ratios":[1.35,1]})
fig.patch.set_facecolor("white")
n=len(rows); h=0.2
for k,(name,idx,c) in enumerate(series):
    ys=[i+(k-1.5)*h for i in range(n)]
    a1.barh(ys,[r[idx]['out_tokens'] for r in rows],height=h,color=c,label=name)
    a2.barh(ys,[r[idx]['cmd_chars'] for r in rows],height=h,color=c)
    for y,r in zip(ys,rows):
        rr=r[idx]
        bad = (not rr['answer_right']) or (not rr['exit_code_right'])
        a1.text(rr['out_tokens']*1.12,y,f"{rr['out_tokens']:,}"+("  ✗" if bad else ""),va="center",fontsize=7.5,color=(RED if bad else "#333"))
        a2.text(rr['cmd_chars']+2,y,str(rr['cmd_chars']),va="center",fontsize=7.5,color="#333")
for a in (a1,a2):
    a.set_yticks(range(n)); a.invert_yaxis()
    for s in ("top","right","left"): a.spines[s].set_visible(False)
    a.tick_params(axis="y",length=0); a.grid(axis="x",color="#eee"); a.set_axisbelow(True)
a1.set_yticklabels([r[0] for r in rows],fontsize=10)
a2.set_yticklabels([])
a1.set_xscale("log"); a1.set_xlim(20, 3e7)
def short(v,_):
    for d,u in ((1e6,"M"),(1e3,"k")):
        if v>=d: return f"{v/d:g}{u}"
    return f"{v:g}"
a1.xaxis.set_major_formatter(FuncFormatter(short))
a1.set_title("Output an AI agent must read (tokens, log scale)",fontsize=11,loc="left",color="#222")
a2.set_title("Command length (characters)",fontsize=11,loc="left",color="#222")
a2.set_xlim(0,175)
a1.legend(loc="lower center",bbox_to_anchor=(0.9,-0.16),ncol=4,frameon=False,fontsize=9.5)
fig.suptitle("indo-cli vs default tools on 20 real repos",x=0.01,ha="left",fontsize=15,fontweight="bold",color="#111")
fig.text(0.01,0.9,"✗ = wrong answer or wrong exit code.  Tokens: tiktoken cl100k_base, stdout+stderr, run with bash -c and no terminal.",fontsize=9,color="#666")
plt.tight_layout(rect=(0,0.03,1,0.9))
plt.savefig("../bench/chart.png",dpi=160)
