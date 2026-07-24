jest
import { start } from './app';
import mongoose from 'mongoose';

describe('App', () => {
  describe('start function', () => {
    it('should connect to MongoDB when MONGODB_URI is set', async () => {
      process.env.MONGODB_URI = 'mongodb://localhost:27017/mydatabase';
      await start();
      expect(mongoose.connection.readyState).toBe(1);
    });

    it('should log error message and not connect to MongoDB when MONGODB_URI is not set', async () => {
      delete process.env.MONGODB_URI;
      await start();
      expect(console.error).toHaveBeenCalledTimes(1);
      expect(mongoose.connection.readyState).toBe(-1);
    });

    it('should start server on port 5000 by default', async () => {
      await start();
      expect(app.listen).toHaveBeenCalledWith(5000, expect.any(Function));
    });

    it('should start server on custom port when PORT is set', async () => {
      process.env.PORT = '8080';
      await start();
      expect(app.listen).toHaveBeenCalledWith(8080, expect.any(Function));
    });
  });
});