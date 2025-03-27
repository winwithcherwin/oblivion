(require ansible *)

(setv output
    (play "Copy stuff" "all"
      (copy "source_fileA" "dest_fileB")
      (copy "source_file1" "dest_file2")))

(print output)
