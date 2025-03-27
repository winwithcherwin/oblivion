(defmacro copy [src dest]
  `(dict
        :name ~(+ "Copy " src " to " dest)
        :copy (dict :src ~src :dest ~dest)))
      
(defmacro dump-yaml [data]
  `(do
    (import ruamel.yaml [YAML])
    (import sys)
    (setv yaml (YAML))
    (.default_flow_style yaml False)
    (.dump yaml ~data sys.stdout)))

(defmacro play [title hosts &rest tasks]
  `(dict
    :name ~title
    :hosts ~hosts
    :tasks (.items ~@tasks)))



(defmacro playbook [&rest plays]
  `(do
    (setv playbook-data (list ~@plays))
    dump-yaml playbook-data))

(defmacro test [&rest input]
  `(print ~@input))
