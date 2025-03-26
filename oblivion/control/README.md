# control

Here is where we do all smart things with the engine. The engine defines the tasks that we have. Control orchestrates the tasks.
If you realise that you do actions back to back with cli and engine, that probably means that you have to write logic in control to orchestrate it.
The Makefile might be a prime example of things that are better put in control.

Look at the following code for example

```
# WIREGUARD
wireguard-init: when-infra-valid ## setup WireGuard
	$(OBLIVION) wireguard register --all
	$(OBLIVION) wireguard write-config --all
```

We have a task where all the nodes are registering themselves to redis, and the the next task is to write the configs, we do this after all workers have registered themselves.
These two things usually go hand in hand, unless you're testing stuff out. We could put this in control.

So control could take all data from register. And then pass that to all nodes by running the write-config task. This way we do not need the queue to store the data.
On top of that, we could inject our own wireguard public key, so that we can become a peer with one or mode nodes. Or we could let the nodes register themselves, but also return the data.
After that we can also register ourselves, and only then do write-config. There are multiple ways to Rome.
I don't do that now because later on we also use the information of register to regenerate the host file on all machines (which we could also immediately do from control, and probably should).
So the nodes can also access the workstation. (cool when we run our local LLMs)

The point is that we will let the reality dictate our decisions. Right now we drive everything from the Makefile in an adhoc way. Later on we can always do smart things with control. The redis
queue gives us shared data and loose coupling. With redis we do not depend on the workstation iniating the tasks to keep track of the data. Pros and cons... We might go for a hybride solution.

For simple things it's quite OK to write to the redis queue for small isolated use cases. For more complicated things we might need full blown orchestration. We will see what practice tells us.

Another challenge / example
```
terraform-apply: terraform-check-vars terraform-init ## terraform apply
	terraform -chdir=terraform apply -auto-approve -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"
	@date > $(BOOTSTRAP_TERRAFORM)
	@echo "Waiting for hosts to settle..."
	@sleep 7
```

We sleep because sometimes things aren't ready (like the oblivion worker restarting) after applying terraform. We could be smarter here by checking some things before returning. This is a perfect use-case for control. This way in the Makefile we can just do the terraform apply with oblivion (via cli).
The cli then executes control to actually run terraform in the right way. Making sure that, the servers
are not only created, but also are functioning correctly. We could easily implement retry logic here.

Basically, control is where we move all the complexity from the Makefile. So the Makefile stays clean.

If we do it right the Makefile essentially then becomes
```
terraform-plan:
    $(OBLIVION) terraform apply
```

Knowing that the value comes from doing various checks and retries.

Control is the brains. It knows the *how*
Engine *propels* has the machinery, the things that happen on the workers.
Core is about the *what*, meaning purpose built modules and packages. Things that could potentially
be shared across control and engine. Think tasks that need access to redis operations.
CLI is executing functions in control. Like a human steers the car.
And `make` makes it easy to run and document all the important commands of the project. Not only limited to operations of cli.

Sometimes there is logic that both control and engine needs. Like creating a certificate authority. Because we want to prevent circular imports, things like this is better suited to be put in core. Control is strictly about driving the engine.

FAQ.
Q: What if we want a task that executes something in control?
A: Good question. Do not do this. It is asking for problems. Recursion is great but not for this.

Q: But how do I manage a machine a fleet of control nodes?
A: Ah, the chicken and egg problem. Even better question. It's quite elementary, you just the cli on one of the machines that you have bootstrapped with oblivion. It's a monorepo. You just need to export the keys and make sure you have access to the state file. This way you can run tasks on yourself. Why wouldn't you? If you expose an API it becomes even better.

