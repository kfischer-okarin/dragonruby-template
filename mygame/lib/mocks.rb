require 'lib/mock_assertions'

def a_mock(&block)
  result = Mock.new
  result.configure_mock(&block) if block
  result
end

class Mock
  def initialize
    clear_method_calls
  end

  def method_calls(method_name)
    @method_calls[method_name] || []
  end

  def clear_method_calls
    @method_calls = {}
  end

  def configure_mock(&block)
    Configurator.new(self).instance_exec(&block)
  end

  # Only configured or already called methods count for respond_to?
  def method_missing(method_name, ...) # rubocop:disable Style/MissingRespondToMissing
    configure_mock do
      responding_to(method_name)
    end
    send(method_name, ...)
  end

  class Configurator
    def initialize(mock)
      @mock = mock
    end

    def responding_to(method_name, &block)
      method_configurator = MethodConfigurator.new(@mock, method_name)
      method_configurator.instance_exec(&block) if block
      method_configurator.define_method
    end
  end

  class MethodConfigurator
    def initialize(mock, method_name)
      @mock = mock
      @method_name = method_name
      @return_values = [nil].cycle
    end

    def always_returning(value)
      @return_values = [value].cycle
    end

    def always_returning_self
      @return_values = [self].cycle
    end

    def returning_values(*values)
      @return_values = values.to_enum
    end

    def define_method
      method_name = @method_name
      return_values = @return_values
      @mock.define_singleton_method(method_name) do |*args, **kwargs|
        @method_calls[method_name] ||= []
        @method_calls[method_name] << [args, kwargs]
        return_values.next
      end
    end
  end
end
