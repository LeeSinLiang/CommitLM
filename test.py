import sys

class Greeter:
	def __init__(self, message):
		self.message = message

	def greet(self):
		return self.message

def main(args):
	greeter = Greeter("Hello, World!")
	output = greeter.greet()
	for char in output:
		sys.stdout.write(char)
	sys.stdout.write('\n')

if __name__ == "__main__":
	main(sys.argv)