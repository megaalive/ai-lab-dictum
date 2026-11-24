#ifndef DICTUM_IR_DIGEST_H
#define DICTUM_IR_DIGEST_H
#include "ir_schema.h"

/* Non-authenticating SHA-256 over exact bytes, bounded to 65536 bytes. */
bool ir_sha256_hex(const unsigned char *data, size_t size, char out[65]);
/* RFC 8785 subset of the validated v1 plan (ASCII property names, exact
 * integers, UTF-8 scalar strings). Excludes only the root digest member.
 * A matching digest is never proof of policy, approval or authenticity. */
bool ir_plan_digest(const struct ir_document *doc, char out[65]);
bool ir_plan_digest_matches(const struct ir_document *doc);
#endif
