nums = []
while True:
    a = int(input('> '))
    if a == 0:
        break
    elif a not in nums:
        nums.append(a)
nums.pop(nums.index(min(nums)))
print(min(nums))