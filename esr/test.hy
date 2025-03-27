(import ruamel.yaml [YAML])
(import sys)

(defmacro copy [src dest]
  `(dict
        :name ~(+ "Copy " src " to " dest)
        :copy (dict :src ~src :dest ~dest)))

;;(.dump YAML (copy "foo" "bar") sys.stdout)

(setv yaml (YAML))
(.dump yaml (dict :foo "bar") sys.stdout)
