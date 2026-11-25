/* Test-only transport. No product or target operation. */
#include "f1_candidate.h"
#include <stdio.h>

int main(void)
{
    unsigned char data[DICTUM_FRAME_MAX+1u];
    const size_t size=fread(data,1,sizeof(data),stdin);
    if (ferror(stdin)) return 2;
    struct ir_document d={0};
    enum ir_status st=ir_parse(&d,data,size);
    if (st==IR_OK) st=f1_candidate_validate(&d);
    ir_destroy(&d);
    puts(ir_status_name(st));
    return ferror(stdout)||fflush(stdout)==EOF?2:0;
}
