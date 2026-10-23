# Android save tests

`test_android_save_files.py` compiles and runs `SaveFilesCoreCheck` on a local JVM. It exercises ZIP validation, save sizes, duplicate and unsafe paths, merge behavior, previous-save recovery, and conflict decisions.

`SaveFilesCheck` and `SaveTestProvider` are instrumentation-only sources. Compile them with the four production save Java classes into the isolated package `io.github.otpr26.savefilestest`, with no launcher intent. Register the provider at `io.github.otpr26.savefilestest.documents` as an exported, grant-URI provider protected by `android.permission.MANAGE_DOCUMENTS`. Never include it in a release APK.

The default instrumentation run injects permission failures and a partial rename failure, checks rollback and conflict refusal, and tests startup reconciliation using synthetic files only.

For a real local-storage check, first select a dedicated folder named `ReTuned-Save-Transfer-Test-<unique suffix>` in the isolated app. Run instrumentation again with `-e shared-check true`. This confirms retained folder permission after restart, committed-save copying, and pulling an external edit. It refuses an ordinary user folder. Remove the isolated package and its synthetic folder afterward.
