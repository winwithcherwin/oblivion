(require ansible *)

(playbook
    (play "Copy files" "all"
      (copy "foo" "bar")
      (copy "foo" "bar")))
