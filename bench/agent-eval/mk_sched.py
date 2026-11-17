import json, random, sys
tasks, arms, reps, seed, out = sys.argv[1].split(","), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
jobs = [{"task": t, "arm": a, "rep": r} for t in tasks for a in arms for r in range(1, reps + 1)]
random.Random(seed).shuffle(jobs)
for i, j in enumerate(jobs): j["order"] = i
json.dump(jobs, open(out, "w")); print(len(jobs))
