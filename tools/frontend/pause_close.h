#ifndef RETUNED_PAUSE_CLOSE_H
#define RETUNED_PAUSE_CLOSE_H
/* A stable native page means the close input has not closed that page. */
static inline unsigned RetunedPausePageStillOpen(unsigned mode) {
    switch (mode) {
        case 0x0c: return 1;
        case 0x10: return 2;
        case 0x14: return 3;
        default: return 0;
    }
}
#endif
