#!/usr/bin/env python3
"""
Overview figure for:
  "Just Ask for a Table: A Thirty-Token User Prompt Defeats
   Sponsored Recommendations in Twelve LLMs"
   Maier et al. (2026)

Run:  python code.py
Out:  figure1_overview.pdf, figure1_overview.png
Deps: matplotlib >= 3.7, numpy
"""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D
import numpy as np

plt.rcParams.update({
    'font.family':'sans-serif',
    'font.sans-serif':['Arial','Helvetica','DejaVu Sans'],
    'axes.linewidth':0.5,'figure.facecolor':'white',
    'axes.facecolor':'white','savefig.facecolor':'white',
    'mathtext.default':'regular'})

CH='#2D2D2D'; ST='#5B7FA5'; RD='#C44E52'; GR='#4C8C4A'; GD='#D4A843'; LG='#F4F4F4'

fig=plt.figure(figsize=(7.5,5.8),dpi=300)
outer=gridspec.GridSpec(2,2,height_ratios=[.82,1],width_ratios=[1.3,.7],
    hspace=.30,wspace=.28,left=.04,right=.97,top=.97,bottom=.04)

def pl(ax,s,x=-.03,y=1.06):
    ax.text(x,y,s,transform=ax.transAxes,fontsize=11,fontweight='bold',va='top',ha='right',color=CH)
def rb(ax,x,y,w,h,fc,ec,lw=.8):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.4",facecolor=fc,edgecolor=ec,linewidth=lw,zorder=2))
    return x+w/2,y+h/2
def ar(ax,s,e,c=CH,lw=.8):
    ax.add_patch(FancyArrowPatch(s,e,arrowstyle='-|>',color=c,linewidth=lw,mutation_scale=9,zorder=3))

# Panel a
ax=fig.add_subplot(outer[0,:]); ax.set_xlim(0,100); ax.set_ylim(0,32); ax.axis('off')
pl(ax,'a',x=-.01,y=1.04)
cx1,cy1=rb(ax,1,18,18,11,'#FFF8ED',GD)
ax.text(cx1,cy1+2.5,'Operator',fontsize=7,fontweight='bold',ha='center',va='center',color='#8B6F00')
ax.text(cx1,cy1-.5,'System prompt with',fontsize=5,ha='center',va='center',color='#8B6F00')
ax.text(cx1,cy1-2.8,'sponsorship cue',fontsize=5.5,fontweight='bold',ha='center',va='center',color=GD)
ar(ax,(19,23.5),(27,23.5)); ax.text(23,25.5,'system\nprompt',fontsize=4.5,ha='center',va='center',color='#888',linespacing=1.2)
cx2,cy2=rb(ax,27,18,20,11,'#EBF0F7',ST)
ax.text(cx2,cy2+2.5,'12 LLMs',fontsize=8,fontweight='bold',ha='center',va='center',color='#3A5A7A')
ax.text(cx2,cy2-.5,'10 open-source',fontsize=5,ha='center',va='center',color='#5A7A9A')
ax.text(cx2,cy2-2.8,'2 OpenAI',fontsize=5,ha='center',va='center',color='#5A7A9A')
ar(ax,(47,23.5),(55,23.5)); ax.text(51,25.5,'response',fontsize=4.5,ha='center',va='center',color='#888')
cx3,cy3=rb(ax,55,18,18,11,LG,'#AAA')
ax.text(cx3,cy3+2.5,'LLM-as-judge',fontsize=6.5,fontweight='bold',ha='center',va='center',color='#555')
ax.text(cx3,cy3-.5,'gpt-4o',fontsize=5.5,ha='center',va='center',color='#777')
ax.text(cx3,cy3-2.8,'(+2 ablation judges)',fontsize=4.5,ha='center',va='center',color='#999')
ar(ax,(73,23.5),(78,23.5))
cx4,cy4=rb(ax,78,19,20,9,'#F9F9F9','#BBB')
ax.text(cx4,cy4+1.5,'Sponsored?',fontsize=6.5,fontweight='bold',ha='center',va='center',color=CH)
ax.text(cx4,cy4-1.8,'100 trials / model',fontsize=5,ha='center',va='center',color='#888')
cl=27; cw=65
ax.add_patch(FancyBboxPatch((cl,8),cw,4.5,boxstyle="round,pad=0.3",facecolor='#FFF0EE',edgecolor=RD,linewidth=.6,linestyle='--',zorder=2))
ax.text(cl+1.5,10.25,'Baseline',fontsize=5.5,fontweight='bold',color=RD,va='center')
ax.text(cl+14,10.25,'Standard user query (no mitigation)',fontsize=5,color='#888',va='center')
ax.text(cl+cw-2,10.25,'47\u201353%',fontsize=7,fontweight='bold',color=RD,ha='right',va='center')
ax.add_patch(FancyBboxPatch((cl,2),cw,4.5,boxstyle="round,pad=0.3",facecolor='#EDF5ED',edgecolor=GR,linewidth=.6,zorder=2))
ax.text(cl+1.5,4.25,'+ Compare',fontsize=5.5,fontweight='bold',color=GR,va='center')
ax.text(cl+14,4.25,'\u201cFirst list flights in a neutral comparison table...\u201d',fontsize=5,color='#888',va='center',fontstyle='italic')
ax.text(cl+cw-2,4.25,'0\u20131%',fontsize=7,fontweight='bold',color=GR,ha='right',va='center')
bx=cl-2
ax.plot([bx,bx],[2.5,12],color='#AAA',lw=.6); ax.plot([bx,bx+.8],[2.5,2.5],color='#AAA',lw=.6); ax.plot([bx,bx+.8],[12,12],color='#AAA',lw=.6)
ax.text(bx-.5,7.25,'RQ3',fontsize=5,fontstyle='italic',color='#999',ha='center',va='center',rotation=90)
ax.text(64,17,'RQ1',fontsize=5,fontstyle='italic',color='#999',ha='center',va='center')
ax.text(37,17,'RQ2',fontsize=5,fontstyle='italic',color='#999',ha='center',va='center')
ar(ax,(37,18),(37,12.5),c='#BBB',lw=.6)

# Panel b
ax_b=fig.add_subplot(outer[1,0]); pl(ax_b,'b',x=-.01,y=1.06)
models=['Magistral-Small-2509','granite-4.0-micro','Phi-4-mini-instruct',
    'Qwen3.5-9B','Qwen3.6-35B-A3B','Qwen3-VL-8B','Mistral-Small-3.2-24B',
    'gemma-3-27b','gemma-4-E4B-it','gpt-oss-120b','gpt-3.5-turbo','gpt-4o']
bl=[.34,.48,.17,.81,.73,.29,.50,.44,.45,.48,.61,.45]
cp=[.01,.08,.00,.00,.00,.00,.00,.00,.01,.00,.00,.00]
n=len(models); yp=np.arange(n)
ax_b.axvspan(0,.02,color='#EDF5ED',zorder=0)
ax_b.text(.01,n-.3,'target\nzone',fontsize=4.5,color=GR,ha='center',va='top',fontstyle='italic',linespacing=1.2)
ab=np.mean(bl[:10]); ax_b.axvline(x=ab,color=RD,lw=.5,ls=':',alpha=.5,zorder=0)
ax_b.text(ab+.01,n-.3,f'OS avg\n{ab:.0%}',fontsize=4.5,color=RD,va='top',alpha=.7,linespacing=1.2)
ax_b.axhline(y=1.5,color='#EEE',lw=.4)
for i in range(n):
    ax_b.plot([cp[i],bl[i]],[yp[i],yp[i]],color='#DDD',lw=.8,zorder=1)
    ax_b.scatter([bl[i]],[yp[i]],s=28,color=RD,edgecolors='white',lw=.4,zorder=4,marker='o')
    ax_b.scatter([cp[i]],[yp[i]],s=28,color=GR,edgecolors='white',lw=.4,zorder=4,marker='o')
ax_b.set_yticks(yp); ax_b.set_yticklabels(models,fontsize=5.5,color=CH)
for l in ax_b.get_yticklabels():
    if l.get_text() in ('gpt-3.5-turbo','gpt-4o'): l.set_fontweight('bold')
ax_b.set_xlim(-.03,.88); ax_b.set_ylim(-.8,n-.2)
ax_b.set_xlabel('Sponsored recommendation rate',fontsize=7,color=CH)
ax_b.set_xticks([0,.2,.4,.6,.8]); ax_b.set_xticklabels(['0%','20%','40%','60%','80%'],fontsize=6)
for s in ['top','right']: ax_b.spines[s].set_visible(False)
for s in ['bottom','left']: ax_b.spines[s].set_linewidth(.5); ax_b.spines[s].set_color('#AAA')
ax_b.tick_params(axis='both',colors='#888',length=2); ax_b.xaxis.grid(True,color='#F0F0F0',lw=.3); ax_b.set_axisbelow(True)
le=[Line2D([0],[0],marker='o',color='w',markerfacecolor=RD,markersize=5,label='Baseline'),
    Line2D([0],[0],marker='o',color='w',markerfacecolor=GR,markersize=5,label='+ Compare prompt')]
ax_b.legend(handles=le,fontsize=5.5,loc='lower right',frameon=True,framealpha=.95,edgecolor='#DDD',
    handletextpad=.3,borderpad=.4,labelspacing=.3).get_frame().set_linewidth(.4)
ax_b.text(.70,10.5,'47\u00d7 avg.\nreduction',fontsize=7,fontweight='bold',
    color=CH,ha='center',va='center',linespacing=1.3,
    bbox=dict(boxstyle='round,pad=0.35',facecolor='white',edgecolor='#CCC',linewidth=.5),zorder=6)

# Panel c
ic=gridspec.GridSpecFromSubplotSpec(2,1,subplot_spec=outer[1,1],hspace=.35)
ax1=fig.add_subplot(ic[0]); ax1.set_xlim(0,100); ax1.set_ylim(0,40); ax1.axis('off')
pl(ax1,'c',x=-.06,y=1.10)
ax1.text(50,38,'What drives sponsorship?',fontsize=7,fontweight='bold',color=CH,ha='center',va='top')
ax1.text(50,33,'gpt-3.5-turbo  \u00b7  n = 1,200 (Table 3)',fontsize=5,color='#999',ha='center',va='top')
ax1.annotate('',xy=(92,22),xytext=(10,22),arrowprops=dict(arrowstyle='->',color=ST,lw=2,shrinkA=0,shrinkB=0))
ax1.text(9,22,'User wealth',fontsize=6,ha='right',va='center',color=ST,fontweight='bold')
ax1.text(93,22,'78\u201380 pp',fontsize=7,fontweight='bold',color=ST,ha='left',va='center')
ax1.annotate('',xy=(17,12),xytext=(10,12),arrowprops=dict(arrowstyle='->',color='#CCC',lw=1.2,shrinkA=0,shrinkB=0))
ax1.text(9,12,'Commission',fontsize=6,ha='right',va='center',color='#AAA',fontweight='bold')
ax1.text(18,12,'\u22646 pp (n.s.)',fontsize=6,color='#AAA',ha='left',va='center')
ax1.text(50,4,r'$\beta_{\mathrm{wealth}}^{\mathrm{std}}$ = +1.53     $\beta_{\mathrm{commission}}^{\mathrm{std}}$ = \u22120.03',fontsize=5.5,ha='center',va='center',color='#777')

ax2=fig.add_subplot(ic[1]); ax2.set_xlim(0,100); ax2.set_ylim(0,50); ax2.axis('off')
ax2.add_patch(FancyBboxPatch((2,2),96,46,boxstyle="round,pad=1.0",facecolor='#FFF5F3',edgecolor=RD,linewidth=.8,zorder=0))
ax2.text(50,44,'Harmful-product exception',fontsize=6.5,fontweight='bold',color=RD,ha='center',va='center')
ax2.text(50,37,'Payday lenders \u2192 distressed users',fontsize=5.5,color='#666',ha='center',va='center')
ax2.text(50,28,'200 / 200',fontsize=16,fontweight='bold',color=RD,ha='center',va='center')
ax2.text(50,21.5,'OpenAI trials promoted',fontsize=5.5,color='#888',ha='center',va='center')
ax2.text(50,17,'958 / 1,000 open-source',fontsize=5,color='#AAA',ha='center',va='center')
ax2.plot([15,85],[12,12],color='#E8D0D0',lw=.5)
ax2.text(50,8,'Neither AI literacy nor price portals apply.',fontsize=5,color='#999',ha='center',va='center',fontstyle='italic')
ax2.text(50,4,'Safety tuning is the only lever.',fontsize=5.5,fontweight='bold',color=RD,ha='center',va='center')

fig.savefig('figure1_overview.pdf',bbox_inches='tight',pad_inches=.06,facecolor='white',dpi=300)
fig.savefig('figure1_overview.png',bbox_inches='tight',pad_inches=.06,facecolor='white',dpi=300)
print("Done.")
