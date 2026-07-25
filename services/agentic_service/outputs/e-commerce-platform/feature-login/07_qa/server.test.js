import { start } from './app';

describe('App', () => {
  it('starts with a database connection when MONGODB_URI is set', async () => {
    process.env.MONGODB_URI = 'mongodb://localhost:27017/mydatabase';
    await start();
    expect(mongoose.connection.readyState).toBe(1);
  });

  it('starts without a database connection when MONGODB_URI is not set', async () => {
    delete process.env.MONGODB_URI;
    await start();
    expect(mongoose.connection.readyState).toBe(-1);
  });

  it('logs an error message when connecting to MongoDB fails', async () => {
    const error = new Error('Mock error');
    mongoose.connect = jest.fn(() => { throw error; });
    await start();
    expect(console.error).toHaveBeenCalledTimes(1);
    expect(console.error).toHaveBeenCalledWith('Failed to connect to MongoDB:', error.message);
  });

  it('logs a warning message when MONGODB_URI is not set', async () => {
    delete process.env.MONGODB_URI;
    await start();
    expect(console.warn).toHaveBeenCalledTimes(1);
    expect(console.warn).toHaveBeenCalledWith('MONGODB_URI is not set -- starting without a database connection.');
  });
});