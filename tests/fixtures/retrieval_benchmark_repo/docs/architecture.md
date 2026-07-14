# Authentication flow

The login route calls `AuthService.authenticate_user` to validate credentials.
After authentication, the route calls `create_access_token` and returns the token.
User profile lookup is a separate operation and does not authenticate passwords.
