#ifndef DICTUM_RENDERER_H
#define DICTUM_RENDERER_H
#include "ir_digest.h"

#define RENDER_MAX 32768u
#define RENDER_TOKEN_MAX 1024u
#define RENDER_ARG_MAX 33u
enum renderer_shell { RENDER_BASH_CLEAN, RENDER_DASH_CLEAN, RENDER_UNKNOWN };
enum renderer_status { RENDER_OK, RENDER_SHELL, RENDER_TOKEN, RENDER_UTF8, RENDER_NONCHAR,
                       RENDER_UNSAFE, RENDER_COUNT, RENDER_SIZE };
struct renderer_token { const unsigned char *data; size_t size; };
/* Actual product path: validates structure and digest of narrative-only
 * plan; never supplies a command. Caller checks policy/context/recipe. */
bool renderer_structured_plan(const struct ir_document *plan);
/* Pure literal encoding only. NOT an authority or recipe validator.
 * F0-C product has no trusted executable bindings; only isolated inert
 * test adapter can call this after separate fixture recipe validation. */
enum renderer_status renderer_check_token(struct renderer_token token);
enum renderer_status renderer_quote_tokens(enum renderer_shell shell,
    const struct renderer_token *tokens, size_t count, char out[RENDER_MAX+1u]);
const char *renderer_status_name(enum renderer_status status);
#endif
