#include "ir_wire.h"
#include <stdio.h>

int main(void)
{
    /* a, U+00E9, U+1F642, z: byte boundaries 0,1,3,7,8. */
    const unsigned char data[] = {0x61,0xc3,0xa9,0xf0,0x9f,0x99,0x82,0x7a};
    const bool boundaries[] = {true,true,false,true,false,false,false,true,true};
    size_t count = 0;
    for (size_t start = 0; start <= sizeof(data) + 1; ++start) {
        for (size_t end = 0; end <= sizeof(data) + 1; ++end) {
            const bool expected = start < end && end <= sizeof(data)
                && boundaries[start] && boundaries[end];
            if (ir_check_span(data,sizeof(data),start,end) != expected) return 1;
            ++count;
        }
    }
    if (ir_check_span(data,sizeof(data),0,SIZE_MAX) ||
        ir_check_span(data,2,0,1) || ir_check_span(NULL,1,0,1) ||
        ir_check_span(data,sizeof(data),SIZE_MAX,SIZE_MAX)) return 1;
    printf("span checks=%zu plus 4 invalid cases\n", count);
    return 0;
}
