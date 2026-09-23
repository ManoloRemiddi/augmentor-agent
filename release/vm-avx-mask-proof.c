/* Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 */
/* Isolate the masked AVX2 load from the Qt/Breeze core dump. No Qt/portal. */
#include <immintrin.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdio.h>
#include <assert.h>
__attribute__((target("avx2"),noinline)) static void check(int *data) {
    __m256i mask=_mm256_setr_epi32(5,4,3,2,1,0,-1,-2);
    __m256i result=_mm256_maskload_epi32(data-2,mask);
    int out[8];_mm256_storeu_si256((__m256i*)out,result);
    for(int n=0;n<6;n++)assert(out[n]==0);
    assert(out[6]==104 && out[7]==105);
}
int main(void){
    if(!__builtin_cpu_supports("avx2")){puts("AVX2 absent");return 77;}
    long page=sysconf(_SC_PAGESIZE);
    char *base=mmap(NULL,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    assert(base!=MAP_FAILED);assert(mprotect(base,page,PROT_NONE)==0);
    int *data=(int*)(base+page);for(int n=0;n<8;n++)data[n]=100+n;
    check(data);puts("PASS: masked-off addresses did not fault");
    munmap(base,page*2);return 0;
}
