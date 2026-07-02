# Hola

Start server by running:
```shell
make build
make up
```


Now you can reach it locally at: [http://localhost:8000]().
Docs at: [http://localhost:8000/docs]().


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

## TODO:
- [ ] Task to have owner and helper setters instead of passing user_id directly. Create _helper_id, _set_owner_id(owner)and property def owner_id/helper_id.
- [ ] Task to have tasks setter instead of... doing nothing currently. See above.
- [ ] Task to expect helper instead of helper_id in task_join()
- [ ] Rename repository create_x() to save_x() methods.
- [ ] Change location to a domain object and add more validation.
- [ ] Login returns the same generic error for both wrong credentials and unverified accounts. Differentiate the unverified case (e.g. distinct status/message and/or a resend-verification endpoint) so users know they need to verify their email.
- [ ] Add social login (third-party OAuth2, e.g. Google) feeding the same token issuer in `match/infra/api/security.py`.