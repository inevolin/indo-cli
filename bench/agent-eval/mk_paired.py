import json, random, sys
tasks, reps, seed, out = sys.argv[1].split(","), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rng = random.Random(seed); pairs = [(t, r) for t in tasks for r in range(1, reps + 1)]; rng.shuffle(pairs); jobs = []
for t, r in pairs:
    arms = ["A", "C"]; rng.shuffle(arms)
    for a in arms: jobs.append({"task": t, "arm": a, "rep": r, "order": len(jobs)})
json.dump(jobs, open(out, "w")); print(len(jobs))
