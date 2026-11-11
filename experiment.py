import time, statistics
from block import Block

def run_experiment(difficulties=(1,2,3,4), runs=10, output="mining_experiment.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    means=[]; lows=[]; highs=[]
    for d in difficulties:
        values=[]
        for i in range(runs):
            b=Block(1, time.time(), "0"*64, [], d, 0)
            start=time.perf_counter(); b.mine(); values.append(time.perf_counter()-start)
        means.append(statistics.mean(values)); lows.append(min(values)); highs.append(max(values))
        print(f"Складність {d}: середнє {means[-1]:.6f} с, мін {lows[-1]:.6f} с, макс {highs[-1]:.6f} с")
    plt.figure(figsize=(8,5))
    plt.errorbar(difficulties, means, yerr=[[m-l for m,l in zip(means,lows)],[h-m for h,m in zip(highs,means)]], marker="o", capsize=4)
    plt.yscale("log"); plt.xlabel("Складність (кількість нулів SHA-256)"); plt.ylabel("Час майнінгу, секунди (логарифмічна шкала)")
    plt.title(f"Час майнінгу: {runs} запусків на рівень"); plt.grid(True, which="both", alpha=.3); plt.tight_layout(); plt.savefig(output,dpi=160)
    print("Графік збережено:",output)
