# Real-World Examples for `indo`

This document contains 50+ real-world examples of using `indo` to manage microservices, multi-repo setups, and directory groups.

`indo` is the default name. In zsh you can also type `in`. In Bash, `in` is a reserved word, so use `indo`.

## Git Operations

1. **Check status across all repos**
   ```bash
   indo * git status -s
   ```
   *Quickly see which microservices have uncommitted changes.*

2. **Pull latest changes everywhere**
   ```bash
   indo -P 4 * git pull origin main
   ```
   *Update all repos in parallel (4 at a time).*

3. **Checkout a specific branch if it exists**
   ```bash
   indo * "git checkout feature/login || git checkout main"
   ```
   *Try to switch to feature branch, fallback to main.*

4. **Create a new release branch**
   ```bash
   indo services/* git checkout -b release/v2.0
   ```

5. **Prune deleted remote branches**
   ```bash
   indo * git fetch -p
   ```

6. **See last commit in every repo**
   ```bash
   indo * "git log -1 --format='%h %s'"
   ```

7. **Stash changes across all services**
   ```bash
   indo services/* git stash
   ```

8. **Discard all local changes (Danger!)**
   ```bash
   indo * git reset --hard HEAD
   ```

9. **Tag a release across multiple packages**
   ```bash
   indo packages/* git tag v1.0.0
   ```

10. **Push tags**
    ```bash
    indo packages/* git push origin v1.0.0
    ```

## Node.js / JavaScript

11. **Install dependencies (clean install)**
    ```bash
    indo -P 4 packages/* npm ci
    ```

12. **Update a specific package everywhere**
    ```bash
    indo * "pnpm update lodash"
    ```

13. **Run tests for a specific scope**
    ```bash
    indo packages/* npm test
    ```

14. **Check for outdated dependencies**
    ```bash
    indo services/* npm outdated
    ```

15. **Audit for vulnerabilities**
    ```bash
    indo * npm audit --production
    ```

16. **Build all frontend apps**
    ```bash
    indo apps/web-* npm run build
    ```

17. **Remove node_modules (Fresh start)**
    ```bash
    indo * "rm -rf node_modules package-lock.json"
    ```

18. **Initialize new projects**
    ```bash
    indo * npm init -y
    ```

19. **Run a custom script if it exists**
    ```bash
    indo * "npm run lint || echo 'No lint script found'"
    ```

20. **Upgrade interactive (using shell features)**
    ```bash
    indo * "ncu -u && npm install"
    ```

## Docker & Microservices

21. **Build all Docker images**
    ```bash
    indo -P 2 services/* docker build -t my-app/service .
    ```
    *Note: This builds them all with the SAME tag name, usually you want dynamic tags.*

22. **Docker build with dynamic directory name**
    ```bash
    indo services/* "docker build -t app/\$(basename \$PWD) ."
    ```
    *Uses shell expansion to tag image with directory name.*

23. **Stop specific containers**
    ```bash
    indo services/auth,services/user docker-compose down
    ```

24. **Restart services**
    ```bash
    indo * "docker-compose restart app"
    ```

25. **View logs tail**
    ```bash
    indo services/* "tail -n 10 logs/service.log"
    ```

26. **Clean up Docker artifacts**
    ```bash
    indo * docker system prune -f
    ```

## File Management & Cleanup

27. **Delete temporary files**
    ```bash
    indo * "rm -rf dist/ .cache/ tmp/"
    ```

28. **Find large files**
    ```bash
    indo * "find . -type f -size +100M"
    ```

29. **Count lines of code**
    ```bash
    indo src/* "wc -l *.ts"
    ```

30. **Replace string in files (Sed)**
    ```bash
    indo * "sed -i 's/foo/bar/g' config.yaml"
    ```

31. **Rename a config file**
    ```bash
    indo * "mv config.local.json config.json"
    ```

32. **Create missing directories**
    ```bash
    indo * mkdir -p .github/workflows
    ```

33. **Copy a standard file to all repos**
    ```bash
    indo * cp ~/templates/LICENSE .
    ```

## System & Diagnostics

34. **Check disk usage of directories**
    ```bash
    indo * du -sh .
    ```

35. **Check active ports (Mac/Linux)**
    ```bash
    indo * "lsof -i -P | grep LISTEN"
    ```

36. **Verify standard file existence**
    ```bash
    indo * "[ -f README.md ] && echo 'OK' || echo 'Missing README'"
    ```

37. **Print current version from package.json**
    ```bash
    indo * "jq .version package.json"
    ```

38. **Check python version**
    ```bash
    indo services/* python --version
    ```

## Advanced Scripting

39. **Chain multiple failures**
    ```bash
    indo * "lint || echo 'Lint failed' >> errors.log"
    ```

40. **Conditional execution based on file presence**
    ```bash
    indo * "if [ -f requirements.txt ]; then pip install -r requirements.txt; fi"
    ```

41. **Run a local script in remote directories**
    ```bash
    indo services/* ~/scripts/health-check.sh
    ```

42. **Grep across multiple repos**
    ```bash
    indo * "grep -r 'TODO' src/ | head -n 5"
    ```

43. **Generate a report**
    ```bash
    indo * "echo \"\$(basename \$PWD): \$(git rev-parse HEAD)\" >> ~/report.txt"
    ```

44. **Export ENV vars per command**
    ```bash
    indo * "NODE_ENV=production npm run build"
    ```

## Python

45. **Install requirements**
    ```bash
    indo services/* pip install -r requirements.txt
    ```

46. **Format code**
    ```bash
    indo * black .
    ```

47. **Run Pytest**
    ```bash
    indo -P 4 * pytest
    ```

## Terraform / Infrastructure

48. **Format TF files**
    ```bash
    indo infra/* terraform fmt
    ```

49. **Validate configurations**
    ```bash
    indo infra/* terraform validate
    ```

50. **Plan changes**
    ```bash
    indo infra/stacks/* "terraform plan -out=tfplan"
    ```
