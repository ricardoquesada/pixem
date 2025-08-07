# Pixem

## Run

```shell
make venv
source venv/bin/activate
make run
```

## Update dependencies

### Pre Commit

```shell
pre-commit autoupdate
```

### requirements.txt

From PyCharm, update dependencies, then:

```shell
pip freeze > requirements.txt
```
