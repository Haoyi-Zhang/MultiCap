"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def capability(out):
    d=Drawing((0,0,14.7,8.7))
    d.box("den",7.35,7.8,7.5,1.0,"Typed bag denotation and input domain\n$P:\\mathrm{Bag}\\,\\tau,\\quad\\mathcal{D}_P$",size=9)
    boxes=[
       ("rep",3.85,5.65,"Restartable replay\npure acyclic program; repeatable sources\n$T=0$ above sufficient stack budget"),
       ("bit",10.85,5.65,"Finite bit barrier\nfinite-domain function $F$, static trace\n$T=2(K_F-B)^+$ bit transfers"),
       ("pos",3.85,2.45,"Positive count-word barrier\nscalar bilinear $f_A$ on natural inputs\n$T=2(\\rho_{\\mathbb{N}}(A)-M)^+$ words"),
       ("occ",10.85,2.45,"Occurrence-record cache\nforced all-pairs, identity-preserving plan\n$R=nm+1$ reads for two slots")]
    for name,x,y,label in boxes:d.box(name,x,y,6.4,1.8,label,size=8.5)
    for name in ("rep","bit"):d.edge("den",name)
    d.arrow(d.point("den","w"),d.point("pos","w"),via=((.2,7.8),(.2,2.45)))
    d.arrow(d.point("den","e"),d.point("occ","e"),via=((14.5,7.8),(14.5,2.45)))
    d.text(7.35,.65,"Each branch fixes its representation, observations and charged unit.",size=8.5)
    d.save(out,"capability-map")

def costs(out):
    d=Drawing((0,0,14.5,4.7))
    for name,x,label in [("source",1.65,"Immutable\nsources"),("eval",7.25,"Working\nevaluator"),("out",12.85,"Output\nsink")]:
        d.box(name,x,3.5,2.8,1.0,label)
    d.box("store",7.25,1,2.8,1.0,"Derived\nstore")
    d.edge("source","eval",sa="e",sb="w");d.edge("eval","out",sa="e",sb="w")
    d.text(4.45,4.1,"source reads $R$",size=8.5);d.text(10.05,4.1,"output writes $O$",size=8.5)
    d.arrow((6.55,3),(6.55,1.5),dashed=True);d.arrow((7.95,1.5),(7.95,3),dashed=True)
    d.text(5.2,2.25,"writes $W$",size=8.5);d.text(9.25,2.25,"reads $L$",size=8.5)
    d.save(out,"cost-coordinates")

def barrier(out):
    d=Drawing((0,0,14.7,5.2))
    d.box("pre",1.55,3.25,2.6,1.15,"Prefix\nsees $x$")
    d.box("fast",5,3.25,2.6,1.15,"$B$ fast bits\npersist")
    d.box("slow",5,1.35,2.6,1.0,"$s$ slow bits\nwrite then read")
    d.box("bar",8.25,2.55,1.1,3.35,"",dashed=True)
    d.text(8.25,2.55,"one-way\nbarrier",size=8)
    d.box("post",10.85,3.25,2.6,1.15,"Continuation\nsees $y$")
    d.box("out",13.75,3.25,1.8,1.15,"Output\n$F(x,y)$",size=8.5)
    d.edge("pre","fast",sa="e",sb="w");d.edge("fast","bar",sa="e",sb="w")
    d.edge("bar","post",sa="e",sb="w");d.edge("post","out",sa="e",sb="w")
    d.text(3.25,4.1,"summary",size=8.5)
    d.arrow(d.point("pre","s"),d.point("slow","w"),via=((1.55,1.35),))
    d.text(2.7,1.65,"spill",size=8)
    d.arrow(d.point("slow","s"),(8.25,.875),via=((5,.4),(8.25,.4)))
    d.text(6.7,.65,"reload",size=8)
    d.text(7.35,4.8,"Static addresses; cleared transient state; output follows the barrier.",size=8.5)
    d.save(out,"barrier-machine")

def factor(out):
    d=Drawing((0,0,14.7,4.1))
    for name,x,w,label in [
       ("f",1.6,2.8,"Certificate\n$A=UV$, width $r$"),
       ("p",5,3.1,"Prefix\n$s_\\ell=U_{\\cdot\\ell}^{\\mathsf{T}}x$"),
       ("b",8.6,3.1,"Barrier\nkeep $\\min(M,r)$\nspill $(r-M)^+$"),
       ("c",12.35,3.8,"Continuation\n$s^{\\mathsf{T}}Vy$")]:
        d.box(name,x,2.7,w,1.45,label,size=8.5)
    for a,b in [("f","p"),("p","b"),("b","c")]:d.edge(a,b,sa="e",sb="w")
    d.text(10.4,1.55,"restore once",size=8)
    d.arrow(d.point("c","s"),(12.35,.6))
    d.text(12.35,.35,"$f_A(x,y)$",size=9)
    d.save(out,"factor-compiler")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outdir",type=Path,default=Path(__file__).resolve().parents[1]/"paper"/"figures")
    out=parser.parse_args().outdir;out.mkdir(parents=True,exist_ok=True)
    for draw in (capability,costs,barrier,factor):draw(out)
if __name__=="__main__":main()
