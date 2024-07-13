# base-project: Base project environment

---

# 1. Development environment

- [Dev container](https://code.visualstudio.com/docs/devcontainers/containers)
  - `.devcontainer/devcontainer.json`
- Poetry
  - `pyproject.toml`
  - `poetry.lock`
- Docker
  - `Dockerfile`
  - `docker-compose.yml`

# 2. Directory structure

```bash
.
├── Dockerfile
├── README.md
├── base_project
│   ├── launch.py
│   └── core
│       ├── __init__.py
│       ├── depth_logging.py
│       ├── files.py
│       ├── global_settings.py
│       ├── timer.py
│       └── utils.py
├── docker-compose.yml
├── poetry.lock
├── pyproject.toml
└── pytest.ini
```

# 3. Utilities

## 3.1 Timer

1. Context manager

   - `Timer(name)`

   ```python
   from base_project.core import Timer

   with Timer("Code1"):
       sleep(1)
   ```

   ```
   * Code1        | 1.00s (0.02m)
   ```

2. Decorator

   - `@Timer(name)`
   - `@T`

   ```python
   from base_project.core import Timer, T

   @Timer("fn1")
   def fn1():
       sleep(1)

   @T
   def fn2():
       sleep(1)

   fn1()
   fn2()
   ```

   ```
   * fn1          | 1.00s (0.02m)
   * Elapsed time | 1.00s (0.02m)
   ```

## 3.2 Depth Logging

1. Decorator

   - `@D`

   ```python
   from base_project.core import D


   @D
   def main():
       main1()
       main2()


   @D
   def main1():
       main11()
       main12()


   @D
   def main11():
       return


   @D
   def main12():
       return


   @D
   def main2():
       main21()


   @D
   def main21():
       return


   if __name__ == "__main__":
       main()
   ```

   ```
     1            | main()
     1.1          | main1()
     1.1.1        | main11()
   * 1.1.1        | 0.00s (0.00m)
     1.1.2        | main12()
   * 1.1.2        | 0.00s (0.00m)
   * 1.1          | 0.00s (0.00m)
     1.2          | main2()
     1.2.1        | main21()
   * 1.2.1        | 0.00s (0.00m)
   * 1.2          | 0.00s (0.00m)
   * 1            | 0.00s (0.00m)
   ```
