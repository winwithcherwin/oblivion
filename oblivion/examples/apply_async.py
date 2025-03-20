from tasks import add

result = add.apply_async(args=[3,5], queue="server-1")
print(result.get())

result = add.apply_async(args=[4,5], queue="server-0")
print(result.get())
