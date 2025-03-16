# Hola

Start server by running:
```shell
make build
make up
```


Now you can reach it locally at: [http://localhost:8000].
Docs at: [http://localhost:8000/docs].


A selection of cool `make` commands:

| command     | description                                       |
|-------------|---------------------------------------------------|
| make build  | Build the container.                              |
| make up     | Run the container.                                |
| make bash   | Open shell in the container.                      |
| make tests  | Run `pytest`.                                     |
| make format | Run linting scripts: `isort`, `mypy` and `black`. |

## Dependencies

Add new dependency by running in the container:

```shell
uv add "dependency==version"
```

