# TODO: password change security

Open concerns from the edit-profile work, most serious first. Keeping
`current_password`/`new_password` out of Sentry is already done (`SENTRY_DENYLIST`).

- [ ] **Old logins stay valid after a password change (high).** Tokens are
  stateless JWTs and the refresh token lives 7 days, so an attacker who stole a
  session stays signed in after the owner changes the password.
  Fix: add `token_version` to users (migration), put it in the JWT, reject
  tokens with an older version, bump it on password change. Return fresh tokens
  from `PUT /user/me/password` (`200` + `TokenSchema` instead of `204`) and
  store them in the frontend. About 2 hours, backend and frontend.

- [ ] **No limit on wrong current-password guesses (medium).** With a stolen
  token, `PUT /user/me/password` can be used to guess the current password
  without limit, and every guess costs an argon2 hash (CPU exhaustion).
  `/user/login` has the same gap. Fix: after 5 failures per user in 15 minutes,
  answer `429`; cover login too. About 1 to 2 hours.

- [ ] **No "your password was changed" email (medium).** The owner can't notice
  a takeover. Fix: send one through `user_messaging_client` after a successful
  change. About 30 minutes.

- [ ] **422 responses echo passwords back (low).** FastAPI puts the rejected
  `input` in validation errors; for "new must differ from current" that is the
  whole body with both passwords, so they land in browser devtools and client
  logs. Fix: strip `input` from 422 errors on `PUT /user/me/password`.
  About 30 minutes.

Nice to have: a maximum password length (for example 128) to bound request size
and hashing work, and a breached-password check (Have I Been Pwned range API).
