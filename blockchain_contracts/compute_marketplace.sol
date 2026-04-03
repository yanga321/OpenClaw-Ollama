// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title OpenClaw Compute Marketplace
 * @author OpenClaw Team
 * @notice Decentralized marketplace for distributed AI compute on OTG drives
 * 
 * Features:
 * - Credit-based incentive system
 * - Task submission & verification
 * - Automatic payment distribution
 * - Reputation tracking
 */
contract ComputeMarketplace {
    
    // Structs
    struct Provider {
        string deviceId;
        uint256 credits;
        uint256 tasksCompleted;
        uint256 reputation;
        bool isActive;
        mapping(uint256 => Task) taskHistory;
    }
    
    struct Task {
        uint256 id;
        address requester;
        address provider;
        string taskHash;
        uint256 rewardCredits;
        TaskStatus status;
        uint256 createdAt;
        uint256 completedAt;
        string resultHash;
    }
    
    enum TaskStatus {
        Pending,
        InProgress,
        Completed,
        Failed,
        Disputed
    }
    
    // State Variables
    mapping(address => Provider) public providers;
    mapping(uint256 => Task) public tasks;
    mapping(address => uint256) public userCreditBalances;
    
    uint256 public taskCounter;
    uint256 public constant MIN_STAKE = 10;
    uint256 public constant BASE_REWARD = 100;
    uint256 public constant REPUTATION_BONUS = 5;
    
    address public owner;
    
    // Events
    event ProviderRegistered(address indexed provider, string deviceId);
    event TaskCreated(uint256 indexed taskId, address indexed requester, uint256 reward);
    event TaskAccepted(uint256 indexed taskId, address indexed provider);
    event TaskCompleted(uint256 indexed taskId, address indexed provider, string resultHash);
    event CreditsTransferred(address from, address to, uint256 amount);
    event ReputationUpdated(address indexed provider, uint256 newReputation);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }
    
    modifier validProvider(address provider) {
        require(providers[provider].isActive, "Provider not active");
        _;
    }
    
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @dev Register as a compute provider
     * @param _deviceId Unique device identifier
     */
    function registerProvider(string memory _deviceId) external {
        require(!providers[msg.sender].isActive, "Already registered");
        
        providers[msg.sender] = Provider({
            deviceId: _deviceId,
            credits: 100, // Starting credits
            tasksCompleted: 0,
            reputation: 0,
            isActive: true
        });
        
        emit ProviderRegistered(msg.sender, _deviceId);
    }
    
    /**
     * @dev Submit a new compute task
     * @param _taskHash Hash of the task data
     * @param _rewardCredits Reward in credits
     * @return taskId The ID of the created task
     */
    function submitTask(string memory _taskHash, uint256 _rewardCredits) 
        external 
        returns (uint256) 
    {
        require(_rewardCredits >= BASE_REWARD, "Reward too low");
        require(userCreditBalances[msg.sender] >= _rewardCredits, "Insufficient credits");
        
        taskCounter++;
        
        tasks[taskCounter] = Task({
            id: taskCounter,
            requester: msg.sender,
            provider: address(0),
            taskHash: _taskHash,
            rewardCredits: _rewardCredits,
            status: TaskStatus.Pending,
            createdAt: block.timestamp,
            completedAt: 0,
            resultHash: ""
        });
        
        // Escrow credits
        userCreditBalances[msg.sender] -= _rewardCredits;
        
        emit TaskCreated(taskCounter, msg.sender, _rewardCredits);
        
        return taskCounter;
    }
    
    /**
     * @dev Accept a task as a provider
     * @param _taskId The task ID to accept
     */
    function acceptTask(uint256 _taskId) external validProvider(msg.sender) {
        Task storage task = tasks[_taskId];
        
        require(task.status == TaskStatus.Pending, "Task not available");
        require(providers[msg.sender].credits >= MIN_STAKE, "Insufficient provider credits");
        
        task.provider = msg.sender;
        task.status = TaskStatus.InProgress;
        
        emit TaskAccepted(_taskId, msg.sender);
    }
    
    /**
     * @dev Complete a task and submit results
     * @param _taskId The task ID to complete
     * @param _resultHash Hash of the result data
     */
    function completeTask(uint256 _taskId, string memory _resultHash) external {
        Task storage task = tasks[_taskId];
        
        require(task.status == TaskStatus.InProgress, "Task not in progress");
        require(msg.sender == task.provider, "Not task provider");
        
        task.resultHash = _resultHash;
        task.status = TaskStatus.Completed;
        task.completedAt = block.timestamp;
        
        // Update provider stats
        Provider storage provider = providers[msg.sender];
        provider.tasksCompleted++;
        provider.reputation += REPUTATION_BONUS;
        
        // Calculate reward with reputation bonus
        uint256 totalReward = task.rewardCredits + 
            (provider.reputation * REPUTATION_BONUS / 100);
        
        // Transfer credits to provider
        userCreditBalances[msg.sender] += totalReward;
        
        emit TaskCompleted(_taskId, msg.sender, _resultHash);
        emit ReputationUpdated(msg.sender, provider.reputation);
    }
    
    /**
     * @dev Add credits to user balance
     * @param _amount Amount of credits to add
     */
    function addCredits(uint256 _amount) external {
        userCreditBalances[msg.sender] += _amount;
    }
    
    /**
     * @dev Transfer credits to another user
     * @param _to Recipient address
     * @param _amount Amount to transfer
     */
    function transferCredits(address _to, uint256 _amount) external {
        require(userCreditBalances[msg.sender] >= _amount, "Insufficient credits");
        
        userCreditBalances[msg.sender] -= _amount;
        userCreditBalances[_to] += _amount;
        
        emit CreditsTransferred(msg.sender, _to, _amount);
    }
    
    /**
     * @dev Get task details
     * @param _taskId The task ID
     * @return Task details
     */
    function getTask(uint256 _taskId) external view returns (
        address requester,
        address provider,
        string memory taskHash,
        uint256 rewardCredits,
        TaskStatus status,
        uint256 createdAt,
        string memory resultHash
    ) {
        Task memory task = tasks[_taskId];
        return (
            task.requester,
            task.provider,
            task.taskHash,
            task.rewardCredits,
            task.status,
            task.createdAt,
            task.resultHash
        );
    }
    
    /**
     * @dev Get provider details
     * @param _provider Provider address
     * @return Provider details
     */
    function getProvider(address _provider) external view returns (
        string memory deviceId,
        uint256 credits,
        uint256 tasksCompleted,
        uint256 reputation,
        bool isActive
    ) {
        Provider memory provider = providers[_provider];
        return (
            provider.deviceId,
            provider.credits,
            provider.tasksCompleted,
            provider.reputation,
            provider.isActive
        );
    }
    
    /**
     * @dev Get user credit balance
     * @param _user User address
     * @return Credit balance
     */
    function getCreditBalance(address _user) external view returns (uint256) {
        return userCreditBalances[_user];
    }
}
