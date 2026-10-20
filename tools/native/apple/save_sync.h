// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#if defined(__APPLE__)
extern "C" {
void RetunedSaveSyncConfigure(const char* saves);
void RetunedSaveSyncTick(bool startup);
void RetunedSaveSyncRequest();
void RetunedSaveSyncCommitted();
bool RetunedSaveSyncEnabled();
void RetunedSaveSyncSetEnabled(bool enabled);
void RetunedSaveSyncStatus(char* text, unsigned long size);
bool RetunedSaveSyncConflict();
void RetunedSaveSyncResolve(bool useCloud);
}
#else
inline void RetunedSaveSyncConfigure(const char*) {}
inline void RetunedSaveSyncTick(bool) {}
inline void RetunedSaveSyncCommitted() {}
#endif
